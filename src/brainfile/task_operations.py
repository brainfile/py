"""brainfile.task_operations

File-based task operations for per-task file architecture (v2).

These functions operate on individual task files in ``.brainfile/board/``
and ``.brainfile/logs/``. Unlike the v1 board operations (operations.py),
these have filesystem side effects (reading/writing/moving files).

This mirrors TS core v2 ``taskOperations.ts``.
"""

from __future__ import annotations

# ruff: noqa: N802,N803,N815
import os
import re
from datetime import datetime
from typing import Literal, TypedDict

from .models import Task, TaskDocument, Subtask
from .task_file import (
    readTaskFile,
    readTasksDir,
    taskFileName,
    writeTaskFile,
)


class TaskOperationResult(TypedDict, total=False):
    """Result of a file-based task operation."""

    success: bool
    task: Task | None
    filePath: str | None
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
    dueDate: str
    relatedFiles: list[str]
    template: Literal["bug", "feature", "refactor"]
    subtasks: list[str]
    parentId: str
    """Optional parent task/document ID for first-class parent-child linking."""
    type: str
    """Document type (e.g., 'epic', 'adr'). When set, IDs use this as prefix (epic-1, adr-1)."""


class TaskFilters(TypedDict, total=False):
    """Filters for listing tasks."""

    column: str
    tag: str
    priority: Literal["low", "medium", "high", "critical"]
    assignee: str
    parentId: str


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
    docs = readTasksDir(board_dir) + readTasksDir(logs_dir)

    # Prefer first-class parentId links when present.
    linked = [doc for doc in docs if doc.task.parent_id == epic_id]
    if linked:
        return [{"id": doc.task.id, "title": doc.task.title} for doc in linked]

    if not child_ids:
        return []

    title_by_id: dict[str, str] = {}
    for doc in docs:
        if doc.task.id not in title_by_id:
            title_by_id[doc.task.id] = doc.task.title

    child_tasks: list[ChildTaskSummary] = []
    for child_id in child_ids:
        title = title_by_id.get(child_id)
        if title:
            child_tasks.append({"id": child_id, "title": title})

    return child_tasks


def _build_child_tasks_section(child_tasks: list[ChildTaskSummary]) -> str:
    if not child_tasks:
        return "## Child Tasks\nNo child tasks recorded."

    lines = [f"- {child['id']}: {child['title']}" for child in child_tasks]
    return "## Child Tasks\n" + "\n".join(lines)


def generateNextFileTaskId(
    boardDir: str, logsDir: str | None = None, typePrefix: str = "task"
) -> str:
    """Generate the next task ID by scanning an existing tasks directory.

    When ``typePrefix`` is provided (e.g., "epic"), generates IDs like ``epic-1``
    and only scans for IDs matching that prefix. Defaults to "task".
    """

    max_num = 0
    escaped = re.escape(typePrefix)
    pattern = re.compile(rf"^{escaped}-(\d+)$")

    def scan_dir(dir_path: str) -> None:
        nonlocal max_num
        docs = readTasksDir(dir_path)
        for doc in docs:
            match = pattern.match(doc.task.id)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num

    scan_dir(boardDir)
    if logsDir:
        scan_dir(logsDir)

    return f"{typePrefix}-{max_num + 1}"


def addTaskFile(
    boardDir: str,
    input: TaskFileInput,
    body: str = "",
    logsDir: str | None = None,
) -> TaskOperationResult:
    """Add a new task file to the tasks directory."""

    if not input.get("title") or not input["title"].strip():
        return {"success": False, "error": "Task title is required"}

    if not input.get("column") or not input["column"].strip():
        return {"success": False, "error": "Task column is required"}

    # Determine ID prefix from type (e.g., type="epic" -> prefix "epic" -> "epic-1")
    type_prefix = input.get("type") or "task"
    task_id = input.get("id") or generateNextFileTaskId(boardDir, logsDir, type_prefix)
    now = datetime.now().isoformat()

    # Build subtasks if provided
    subtasks_input = input.get("subtasks")
    subtasks: list[Subtask] | None = None
    if subtasks_input:
        subtasks = [
            Subtask(
                id=f"{task_id}-{i + 1}",
                title=title.strip(),
                completed=False,
            )
            for i, title in enumerate(subtasks_input)
        ]

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
        dueDate=input.get("dueDate"),
        relatedFiles=input.get("relatedFiles"),
        template=input.get("template"),
        parentId=input.get("parentId").strip() if input.get("parentId") else None,
        subtasks=subtasks,
        createdAt=now,
    )

    file_path = os.path.join(boardDir, taskFileName(task_id))

    try:
        writeTaskFile(file_path, task, body)
        return {"success": True, "task": task, "filePath": file_path}
    except Exception as e:
        return {"success": False, "error": f"Failed to write task file: {e}"}


def moveTaskFile(
    taskPath: str,
    newColumn: str,
    newPosition: int | None = None,
) -> TaskOperationResult:
    """Move a task to a different column by updating its frontmatter."""

    doc = readTaskFile(taskPath)
    if not doc:
        return {"success": False, "error": f"Failed to read task file: {taskPath}"}

    now = datetime.now().isoformat()
    updated_task = doc.task.model_copy(
        update={
            "column": newColumn,
            "updated_at": now,
        }
    )

    if newPosition is not None:
        updated_task.position = newPosition

    try:
        writeTaskFile(taskPath, updated_task, doc.body)
        return {"success": True, "task": updated_task, "filePath": taskPath}
    except Exception as e:
        return {"success": False, "error": f"Failed to write task file: {e}"}


def completeTaskFile(
    taskPath: str,
    logsDir: str,
) -> TaskOperationResult:
    """Complete a task by moving its file from board/ to logs/ and adding completedAt."""

    doc = readTaskFile(taskPath)
    if not doc:
        return {"success": False, "error": f"Failed to read task file: {taskPath}"}

    now = datetime.now().isoformat()

    # Remove column and position, add completedAt
    task_data = doc.task.model_dump(by_alias=True)
    task_data.pop("column", None)
    task_data.pop("position", None)
    task_data["completedAt"] = now
    task_data["updatedAt"] = now

    completed_task = Task.model_validate(task_data)

    dest_path = os.path.join(logsDir, os.path.basename(taskPath))
    completed_body = doc.body

    if doc.task.type == "epic":
        board_dir = os.path.dirname(taskPath)
        child_ids = _extract_epic_child_task_ids(doc.task)
        child_tasks = _resolve_child_tasks(doc.task.id, child_ids, board_dir, logsDir)
        child_tasks_section = _build_child_tasks_section(child_tasks)
        completed_body = _append_body_section(doc.body, child_tasks_section)

    try:
        os.makedirs(logsDir, exist_ok=True)
        writeTaskFile(dest_path, completed_task, completed_body)
        os.remove(taskPath)
        return {"success": True, "task": completed_task, "filePath": dest_path}
    except Exception as e:
        return {"success": False, "error": f"Failed to complete task: {e}"}


def deleteTaskFile(taskPath: str) -> TaskOperationResult:
    """Delete a task file from disk."""

    doc = readTaskFile(taskPath)
    if not doc:
        return {"success": False, "error": f"Failed to read task file: {taskPath}"}

    try:
        os.remove(taskPath)
        return {"success": True, "task": doc.task}
    except Exception as e:
        return {"success": False, "error": f"Failed to delete task file: {e}"}


def appendLog(
    taskPath: str,
    entry: str,
    agent: str | None = None,
) -> TaskOperationResult:
    """Append a timestamped log entry to a task file's ## Log section."""

    doc = readTaskFile(taskPath)
    if not doc:
        return {"success": False, "error": f"Failed to read task file: {taskPath}"}

    now = datetime.now().isoformat()
    attribution = f" [{agent}]" if agent else ""
    log_line = f"- {now}{attribution}: {entry}"

    body = doc.body

    # Find the ## Log section
    log_section_regex = re.compile(r"^## Log\s*$", re.MULTILINE)
    match = log_section_regex.search(body)

    if match:
        # Insert the log entry after the ## Log header
        insert_pos = match.end()
        body = body[:insert_pos] + "\n" + log_line + body[insert_pos:]
    else:
        # Create the section at the end
        if body and not body.endswith("\n"):
            body += "\n"
        if body:
            body += "\n"
        body += "## Log\n" + log_line + "\n"

    updated_task = doc.task.model_copy(update={"updated_at": now})

    try:
        writeTaskFile(taskPath, updated_task, body)
        return {"success": True, "task": updated_task, "filePath": taskPath}
    except Exception as e:
        return {"success": False, "error": f"Failed to append log: {e}"}


def listTasks(
    boardDir: str,
    filters: TaskFilters | None = None,
) -> list[TaskDocument]:
    """List tasks from a directory, with optional filters."""

    docs = readTasksDir(boardDir)

    if filters:
        if filters.get("column"):
            docs = [d for d in docs if d.task.column == filters["column"]]
        if filters.get("tag"):
            docs = [d for d in docs if d.task.tags and filters["tag"] in d.task.tags]
        if filters.get("priority"):
            docs = [d for d in docs if d.task.priority == filters["priority"]]
        if filters.get("assignee"):
            docs = [d for d in docs if d.task.assignee == filters["assignee"]]
        if filters.get("parentId"):
            docs = [d for d in docs if d.task.parent_id == filters["parentId"]]

    def sort_key(doc: TaskDocument):
        col = doc.task.column or ""
        pos = doc.task.position if doc.task.position is not None else float("inf")
        return (col, pos)

    docs.sort(key=sort_key)
    return docs


def findTask(
    boardDir: str,
    taskId: str,
) -> TaskDocument | None:
    """Find a task by ID in a directory."""

    # Fast path: try convention-based filename
    direct_path = os.path.join(boardDir, taskFileName(taskId))
    direct_doc = readTaskFile(direct_path)
    if direct_doc and direct_doc.task.id == taskId:
        return direct_doc

    # Slow path: scan all files
    docs = readTasksDir(boardDir)
    for d in docs:
        if d.task.id == taskId:
            return d
    return None


def searchTaskFiles(
    boardDir: str,
    query: str,
) -> list[TaskDocument]:
    """Search tasks by query string across title, description, and body."""

    normalized_query = query.lower()
    docs = readTasksDir(boardDir)

    results: list[TaskDocument] = []
    for doc in docs:
        title_match = normalized_query in doc.task.title.lower()
        desc_match = (
            doc.task.description.lower() if doc.task.description else ""
        ).find(normalized_query) != -1
        body_match = normalized_query in doc.body.lower()
        tag_match = any(
            normalized_query in t.lower() for t in (doc.task.tags or [])
        )
        if title_match or desc_match or body_match or tag_match:
            results.append(doc)

    return results


def searchLogs(
    logsDir: str,
    query: str,
) -> list[TaskDocument]:
    """Search completed task logs by query string."""
    return searchTaskFiles(logsDir, query)
