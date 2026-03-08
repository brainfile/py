"""brainfile.task_operations

File-based task operations for per-task file architecture (v2).

These functions operate on individual task files in ``.brainfile/board/``
and ``.brainfile/logs/``. Unlike the v1 board operations (operations.py),
these have filesystem side effects (reading/writing/moving files).

This mirrors TS core v2 ``taskOperations.ts``.
"""

from __future__ import annotations

import json
import os
import re
from contextlib import suppress
from typing import Literal, TypedDict

from ._time import utc_now_iso
from .ledger import append_ledger_record, build_ledger_record
from .models import Task, TaskDocument, Subtask
from .templates import generate_subtask_id
from .task_file import (
    read_task_file,
    read_tasks_dir,
    serialize_task_content,
    task_file_name,
    write_task_file,
)
from .types_ledger import BuildLedgerRecordOptions, LedgerRecord


class TaskOperationResult(TypedDict, total=False):
    """Result of a file-based task operation."""

    success: bool
    task: Task | None
    file_path: str | None
    error: str | None


class TaskFileInput(TypedDict, total=False):
    """Input for creating a new task file."""

    id: str
    title: str
    column: str
    position: int
    description: str
    priority: Literal["low", "medium", "high", "critical"]
    tags: list[str]
    assignee: str
    due_date: str
    related_files: list[str]
    template: Literal["bug", "feature", "refactor"]
    subtasks: list[str]
    parent_id: str
    """Optional parent task/document ID for first-class parent-child linking."""
    type: str
    """Document type (e.g., 'epic', 'adr'). When set, IDs use this as prefix (epic-1, adr-1)."""


class TaskFilters(TypedDict, total=False):
    """Filters for listing tasks."""

    column: str
    tag: str
    priority: Literal["low", "medium", "high", "critical"]
    assignee: str
    parent_id: str


class ChildTaskSummary(TypedDict):
    id: str
    title: str


def _append_body_section(body: str, section: str) -> str:
    trimmed = body.rstrip()
    if not trimmed:
        return f"{section}\n"
    return f"{trimmed}\n\n{section}\n"


def _extract_epic_child_task_ids(task: Task) -> list[str]:
    raw_subtasks = task.subtasks
    if not raw_subtasks:
        return []

    child_ids: list[str] = []

    for subtask in raw_subtasks:
        if isinstance(subtask, str) and subtask.strip():
            child_ids.append(subtask.strip())
            continue

        if isinstance(subtask, Subtask):
            if subtask.id and subtask.id.strip():
                child_ids.append(subtask.id.strip())
        elif isinstance(subtask, dict):
            candidate_id = subtask.get("id")
            if isinstance(candidate_id, str) and candidate_id.strip():
                child_ids.append(candidate_id.strip())

    return list(dict.fromkeys(child_ids))  # preserve order, remove duplicates


def _resolve_child_tasks(
    epic_id: str,
    child_ids: list[str],
    board_dir: str,
    logs_dir: str,
) -> list[ChildTaskSummary]:
    docs = read_tasks_dir(board_dir) + read_tasks_dir(logs_dir)

    linked = [doc for doc in docs if doc.task.parent_id == epic_id]
    if linked:
        return [{"id": doc.task.id, "title": doc.task.title} for doc in linked]
    if not child_ids:
        return []

    title_by_id = {doc.task.id: doc.task.title for doc in docs}
    return [
        {"id": child_id, "title": title_by_id[child_id]}
        for child_id in child_ids
        if child_id in title_by_id
    ]


def _build_child_tasks_section(child_tasks: list[ChildTaskSummary]) -> str:
    if not child_tasks:
        return "## Child Tasks\nNo child tasks recorded."

    lines = [f"- {child['id']}: {child['title']}" for child in child_tasks]
    return "## Child Tasks\n" + "\n".join(lines)


def _write_task_file_exclusive(file_path: str, task: Task, body: str) -> None:
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    content = serialize_task_content(task, body)
    with open(file_path, "x", encoding="utf-8") as file:
        file.write(content)


def _rollback_ledger_append(logs_dir: str, record: LedgerRecord) -> None:
    ledger_path = os.path.join(logs_dir, "ledger.jsonl")
    payload = record.model_dump(by_alias=True, exclude_none=True)

    appended_line = json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n"
    appended_bytes = len(appended_line.encode("utf-8"))

    try:
        stat = os.stat(ledger_path)
        new_size = stat.st_size - appended_bytes
        if new_size >= 0:
            with open(ledger_path, "rb+") as file:
                file.truncate(new_size)
    except Exception:
        pass


def _epic_completion_body(task_path: str, logs_dir: str, doc: TaskDocument) -> str:
    if doc.task.type != "epic":
        return doc.body

    board_dir = os.path.dirname(task_path)
    child_ids = _extract_epic_child_task_ids(doc.task)
    child_tasks = _resolve_child_tasks(doc.task.id, child_ids, board_dir, logs_dir)
    child_tasks_section = _build_child_tasks_section(child_tasks)
    return _append_body_section(doc.body, child_tasks_section)


def _complete_task_file_legacy(
    task_path: str,
    logs_dir: str,
    doc: TaskDocument,
    completed_task: Task,
) -> TaskOperationResult:
    dest_path = os.path.join(logs_dir, os.path.basename(task_path))
    completed_body = _epic_completion_body(task_path, logs_dir, doc)

    try:
        _write_task_file_exclusive(dest_path, completed_task, completed_body)
    except FileExistsError:
        return {"success": False, "error": f"Task already exists in logs: {doc.task.id}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to complete task: {e}"}

    try:
        os.remove(task_path)
        return {"success": True, "task": completed_task, "file_path": dest_path}
    except Exception as e:
        with suppress(Exception):
            os.remove(dest_path)
        return {"success": False, "error": f"Failed to finalize completion: {e}"}


def generate_next_file_task_id(
    board_dir: str, logs_dir: str | None = None, type_prefix: str = "task"
) -> str:
    """Generate the next task ID by scanning an existing tasks directory.

    When ``type_prefix`` is provided (e.g., "epic"), generates IDs like ``epic-1``
    and only scans for IDs matching that prefix. Defaults to "task".
    """

    max_num = 0
    escaped = re.escape(type_prefix)
    pattern = re.compile(rf"^{escaped}-(\d+)$")

    def scan_dir(dir_path: str) -> None:
        nonlocal max_num
        docs = read_tasks_dir(dir_path)
        for doc in docs:
            match = pattern.match(doc.task.id)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num

    scan_dir(board_dir)
    if logs_dir:
        scan_dir(logs_dir)

    return f"{type_prefix}-{max_num + 1}"


def _validate_task_input(input: TaskFileInput) -> str | None:
    if not input.get("title") or not input["title"].strip():
        return "Task title is required"
    if not input.get("column") or not input["column"].strip():
        return "Task column is required"
    return None


def _build_subtasks(task_id: str, subtasks_input: list[str] | None) -> list[Subtask] | None:
    if not subtasks_input:
        return None
    return [
        Subtask(
            id=generate_subtask_id(task_id, i),
            title=title.strip(),
            completed=False,
        )
        for i, title in enumerate(subtasks_input)
    ]


def add_task_file(
    board_dir: str,
    input: TaskFileInput,
    body: str = "",
    logs_dir: str | None = None,
) -> TaskOperationResult:
    """Add a new task file to the tasks directory."""

    validation_error = _validate_task_input(input)
    if validation_error:
        return {"success": False, "error": validation_error}

    type_prefix = input.get("type") or "task"
    task_id = input.get("id") or generate_next_file_task_id(board_dir, logs_dir, type_prefix)
    now = utc_now_iso()
    subtasks = _build_subtasks(task_id, input.get("subtasks"))

    task = Task(
        id=task_id,
        title=input["title"].strip(),
        type=input.get("type"),
        column=input["column"].strip(),
        position=input.get("position"),
        description=input.get("description", "").strip() or None,
        priority=input.get("priority"),
        tags=input.get("tags"),
        assignee=input.get("assignee"),
        due_date=input.get("due_date"),
        related_files=input.get("related_files"),
        template=input.get("template"),
        parent_id=input.get("parent_id", "").strip() if input.get("parent_id") else None,
        subtasks=subtasks,
        created_at=now,
    )

    file_path = os.path.join(board_dir, task_file_name(task_id))

    try:
        write_task_file(file_path, task, body)
        return {"success": True, "task": task, "file_path": file_path}
    except Exception as e:
        return {"success": False, "error": f"Failed to write task file: {e}"}


def move_task_file(
    task_path: str,
    new_column: str,
    new_position: int | None = None,
) -> TaskOperationResult:
    """Move a task to a different column by updating its frontmatter."""

    doc = read_task_file(task_path)
    if not doc:
        return {"success": False, "error": f"Failed to read task file: {task_path}"}

    now = utc_now_iso()
    updated_task = doc.task.model_copy(
        update={
            "column": new_column,
            "updated_at": now,
        }
    )

    if new_position is not None:
        updated_task.position = new_position

    try:
        write_task_file(task_path, updated_task, doc.body)
        return {"success": True, "task": updated_task, "file_path": task_path}
    except Exception as e:
        return {"success": False, "error": f"Failed to write task file: {e}"}


def complete_task_file(
    task_path: str,
    logs_dir: str,
    legacy_mode: bool = False,
    summary: str | None = None,
    files_changed: list[str] | None = None,
    column_history: list[str] | None = None,
    validation_attempts: int | None = None,
) -> TaskOperationResult:
    """
    Complete a task by appending to ``logs/ledger.jsonl`` and removing board file.

    When ``legacy_mode`` is True, keeps old behavior of moving markdown files into logs/.
    """

    doc = read_task_file(task_path)
    if not doc:
        return {"success": False, "error": f"Failed to read task file: {task_path}"}

    now = utc_now_iso()

    completed_task = doc.task.model_copy(
        update={
            "column": None,
            "position": None,
            "completed_at": now,
            "updated_at": now,
        }
    )

    if legacy_mode:
        return _complete_task_file_legacy(task_path, logs_dir, doc, completed_task)

    options = BuildLedgerRecordOptions(
        summary=summary,
        files_changed=files_changed,
        completed_at=now,
        column_history=column_history,
        validation_attempts=validation_attempts,
    )
    record = build_ledger_record(completed_task, doc.body, options)

    try:
        ledger_path = append_ledger_record(logs_dir, record)
    except Exception as e:
        return {"success": False, "error": f"Failed to append ledger record: {e}"}

    try:
        os.remove(task_path)
        return {"success": True, "task": completed_task, "file_path": ledger_path}
    except Exception as e:
        _rollback_ledger_append(logs_dir, record)
        return {"success": False, "error": f"Failed to finalize completion: {e}"}


def delete_task_file(task_path: str) -> TaskOperationResult:
    """Delete a task file from disk."""

    doc = read_task_file(task_path)
    if not doc:
        return {"success": False, "error": f"Failed to read task file: {task_path}"}

    try:
        os.remove(task_path)
        return {"success": True, "task": doc.task}
    except Exception as e:
        return {"success": False, "error": f"Failed to delete task file: {e}"}


def append_log(
    task_path: str,
    entry: str,
    agent: str | None = None,
) -> TaskOperationResult:
    """Append a timestamped log entry to a task file's ## Log section."""

    doc = read_task_file(task_path)
    if not doc:
        return {"success": False, "error": f"Failed to read task file: {task_path}"}

    now = utc_now_iso()
    attribution = f" [{agent}]" if agent else ""
    log_line = f"- {now}{attribution}: {entry}"

    body = doc.body
    match = re.compile(r"^## Log\s*$", re.MULTILINE).search(body)
    if match:
        insert_pos = match.end()
        body = body[:insert_pos] + "\n" + log_line + body[insert_pos:]
    else:
        if body and not body.endswith("\n"):
            body += "\n"
        if body:
            body += "\n"
        body += "## Log\n" + log_line + "\n"

    updated_task = doc.task.model_copy(update={"updated_at": now})

    try:
        write_task_file(task_path, updated_task, body)
        return {"success": True, "task": updated_task, "file_path": task_path}
    except Exception as e:
        return {"success": False, "error": f"Failed to append log: {e}"}


def _matches_filters(doc: TaskDocument, filters: TaskFilters) -> bool:
    if filters.get("column") and doc.task.column != filters["column"]:
        return False
    if filters.get("tag") and (not doc.task.tags or filters["tag"] not in doc.task.tags):
        return False
    if filters.get("priority") and doc.task.priority != filters["priority"]:
        return False
    if filters.get("assignee") and doc.task.assignee != filters["assignee"]:
        return False
    return not filters.get("parent_id") or doc.task.parent_id == filters["parent_id"]


def list_tasks(
    board_dir: str,
    filters: TaskFilters | None = None,
) -> list[TaskDocument]:
    """List tasks from a directory, with optional filters."""

    docs = read_tasks_dir(board_dir)
    if filters:
        docs = [doc for doc in docs if _matches_filters(doc, filters)]

    def sort_key(doc: TaskDocument):
        col = doc.task.column or ""
        pos = doc.task.position if doc.task.position is not None else float("inf")
        return (col, pos)

    docs.sort(key=sort_key)
    return docs


def find_task(
    board_dir: str,
    task_id: str,
) -> TaskDocument | None:
    """Find a task by ID in a directory."""

    direct_path = os.path.join(board_dir, task_file_name(task_id))
    direct_doc = read_task_file(direct_path)
    if direct_doc and direct_doc.task.id == task_id:
        return direct_doc

    docs = read_tasks_dir(board_dir)
    for d in docs:
        if d.task.id == task_id:
            return d
    return None


def search_task_files(
    board_dir: str,
    query: str,
) -> list[TaskDocument]:
    """Search tasks by query string across title, description, and body."""

    normalized_query = query.lower()
    docs = read_tasks_dir(board_dir)

    results: list[TaskDocument] = []
    for doc in docs:
        title_match = normalized_query in doc.task.title.lower()
        description = doc.task.description.lower() if doc.task.description else ""
        desc_match = normalized_query in description
        body_match = normalized_query in doc.body.lower()
        tag_match = any(normalized_query in t.lower() for t in (doc.task.tags or []))
        if title_match or desc_match or body_match or tag_match:
            results.append(doc)

    return results


def search_logs(
    logs_dir: str,
    query: str,
) -> list[TaskDocument]:
    """Search completed task logs by query string."""
    return search_task_files(logs_dir, query)
