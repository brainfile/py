"""brainfile.workspace

Workspace detection, path resolution, and body helpers.

This mirrors TS core ``workspace.ts``.

Key concepts
- Uses a ``.brainfile/`` directory.
- Config lives at ``.brainfile/brainfile.md``.
- Active tasks live in ``.brainfile/board/*.md``.
- Completed tasks live in ``.brainfile/logs/*.md``.

All functions are side-effect free except for :func:`ensure_dirs`.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .models import BoardConfig
from .parser import BrainfileParser
from .task_file import read_task_file, read_tasks_dir, task_file_name


@dataclass(frozen=True)
class WorkspaceDirs:
    dot_dir: str
    board_dir: str
    logs_dir: str
    brainfile_path: str


def get_dirs(brainfile_path: str) -> WorkspaceDirs:
    resolved = os.path.abspath(brainfile_path)
    dot_dir = os.path.dirname(resolved)
    return WorkspaceDirs(
        dot_dir=dot_dir,
        board_dir=os.path.join(dot_dir, "board"),
        logs_dir=os.path.join(dot_dir, "logs"),
        brainfile_path=resolved,
    )


def is_workspace(brainfile_path: str) -> bool:
    dirs = get_dirs(brainfile_path)
    return os.path.exists(dirs.board_dir)


def ensure_dirs(brainfile_path: str) -> WorkspaceDirs:
    dirs = get_dirs(brainfile_path)
    os.makedirs(dirs.board_dir, exist_ok=True)
    os.makedirs(dirs.logs_dir, exist_ok=True)
    return dirs


def get_task_file_path(board_dir: str, task_id: str) -> str:
    return os.path.join(board_dir, task_file_name(task_id))


def get_log_file_path(logs_dir: str, task_id: str) -> str:
    return os.path.join(logs_dir, task_file_name(task_id))


def find_task(
    dirs: WorkspaceDirs,
    task_id: str,
    search_logs: bool = False,
) -> dict | None:
    """Find a task across active tasks and optionally logs.

    Returns a dict: {doc, file_path, is_log} or None.
    """

    # Fast path: board convention
    task_path = get_task_file_path(dirs.board_dir, task_id)
    task_doc = read_task_file(task_path)
    if task_doc and task_doc.task.id == task_id:
        return {"doc": task_doc, "file_path": task_path, "is_log": False}

    # Fast path: log convention
    if search_logs:
        log_path = get_log_file_path(dirs.logs_dir, task_id)
        log_doc = read_task_file(log_path)
        if log_doc and log_doc.task.id == task_id:
            return {"doc": log_doc, "file_path": log_path, "is_log": True}

    # Slow path: scan dirs
    board_docs = read_tasks_dir(dirs.board_dir)
    for doc in board_docs:
        if doc.task.id == task_id:
            return {
                "doc": doc,
                "file_path": doc.file_path or task_path,
                "is_log": False,
            }

    if search_logs:
        log_docs = read_tasks_dir(dirs.logs_dir)
        for doc in log_docs:
            if doc.task.id == task_id:
                return {
                    "doc": doc,
                    "file_path": doc.file_path or get_log_file_path(dirs.logs_dir, task_id),
                    "is_log": True,
                }

    return None


_DESCRIPTION_RE = re.compile(r"## Description\n([\s\S]*?)(?=\n## |\n*$)")
_LOG_RE = re.compile(r"## Log\n([\s\S]*?)(?=\n## |\n*$)")


def extract_description(body: str) -> str | None:
    match = _DESCRIPTION_RE.search(body)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def extract_log(body: str) -> str | None:
    match = _LOG_RE.search(body)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def compose_body(description: str | None = None, log: str | None = None) -> str:
    sections: list[str] = []

    if description and description.strip():
        sections.append(f"## Description\n{description.strip()}")

    if log and log.strip():
        sections.append(f"## Log\n{log.strip()}")

    if not sections:
        return ""

    return "\n\n".join(sections) + "\n"


def read_board_config(brainfile_path: str) -> BoardConfig:
    with open(brainfile_path, encoding="utf-8") as f:
        content = f.read()

    data = BrainfileParser.parse(content)
    if not data:
        raise ValueError(f"Failed to parse brainfile: {brainfile_path}")

    return BoardConfig.model_validate(data)
