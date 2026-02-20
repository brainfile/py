"""brainfile.workspace

V2 workspace detection, path resolution, and body helpers.

This mirrors TS core v2 `workspace.ts`.

Key concepts
- V2 uses a `.brainfile/` directory.
- Config lives at `.brainfile/brainfile.md`.
- Active tasks live in `.brainfile/board/*.md`.
- Completed tasks live in `.brainfile/logs/*.md`.

All functions are side-effect free except for :func:`ensureV2Dirs`.
"""

from __future__ import annotations

# ruff: noqa: N802,N803,N815
import os
import re
from dataclasses import dataclass

from .models import Board, TaskDocument
from .parser import BrainfileParser
from .task_file import readTaskFile, readTasksDir, taskFileName


@dataclass(frozen=True)
class V2Dirs:
    dotDir: str
    boardDir: str
    logsDir: str
    brainfilePath: str


def getV2Dirs(brainfilePath: str) -> V2Dirs:
    resolved = os.path.abspath(brainfilePath)
    dot_dir = os.path.dirname(resolved)
    return V2Dirs(
        dotDir=dot_dir,
        boardDir=os.path.join(dot_dir, "board"),
        logsDir=os.path.join(dot_dir, "logs"),
        brainfilePath=resolved,
    )


def isV2(brainfilePath: str) -> bool:
    dirs = getV2Dirs(brainfilePath)
    return os.path.exists(dirs.boardDir)


def ensureV2Dirs(brainfilePath: str) -> V2Dirs:
    dirs = getV2Dirs(brainfilePath)
    os.makedirs(dirs.boardDir, exist_ok=True)
    os.makedirs(dirs.logsDir, exist_ok=True)
    return dirs


def getTaskFilePath(boardDir: str, taskId: str) -> str:
    return os.path.join(boardDir, taskFileName(taskId))


def getLogFilePath(logsDir: str, taskId: str) -> str:
    return os.path.join(logsDir, taskFileName(taskId))


def findV2Task(
    dirs: V2Dirs,
    taskId: str,
    searchLogs: bool = False,
) -> dict | None:
    """Find a task across active tasks and optionally logs.

    Returns a TS-like dict: {doc, filePath, isLog} or None.
    """

    # Fast path: board convention
    task_path = getTaskFilePath(dirs.boardDir, taskId)
    task_doc = readTaskFile(task_path)
    if task_doc and task_doc.task.id == taskId:
        return {"doc": task_doc, "filePath": task_path, "isLog": False}

    # Fast path: log convention
    if searchLogs:
        log_path = getLogFilePath(dirs.logsDir, taskId)
        log_doc = readTaskFile(log_path)
        if log_doc and log_doc.task.id == taskId:
            return {"doc": log_doc, "filePath": log_path, "isLog": True}

    # Slow path: scan dirs
    board_docs = readTasksDir(dirs.boardDir)
    for doc in board_docs:
        if doc.task.id == taskId:
            return {
                "doc": doc,
                "filePath": doc.file_path or task_path,
                "isLog": False,
            }

    if searchLogs:
        log_docs = readTasksDir(dirs.logsDir)
        for doc in log_docs:
            if doc.task.id == taskId:
                return {
                    "doc": doc,
                    "filePath": doc.file_path or getLogFilePath(dirs.logsDir, taskId),
                    "isLog": True,
                }

    return None


_DESCRIPTION_RE = re.compile(r"## Description\n([\s\S]*?)(?=\n## |\n*$)")
_LOG_RE = re.compile(r"## Log\n([\s\S]*?)(?=\n## |\n*$)")


def extractDescription(body: str) -> str | None:
    match = _DESCRIPTION_RE.search(body)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def extractLog(body: str) -> str | None:
    match = _LOG_RE.search(body)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def composeBody(description: str | None = None, log: str | None = None) -> str:
    sections: list[str] = []

    if description and description.strip():
        sections.append(f"## Description\n{description.strip()}")

    if log and log.strip():
        sections.append(f"## Log\n{log.strip()}")

    if not sections:
        return ""

    return "\n\n".join(sections) + "\n"


def readV2BoardConfig(brainfilePath: str) -> Board:
    with open(brainfilePath, encoding="utf-8") as f:
        content = f.read()

    result = BrainfileParser.parse_with_errors(content)
    if not result.board:
        raise ValueError(f"Failed to parse brainfile: {result.error}")

    board = result.board
    # Ensure tasks arrays exist (config-only brainfile may omit them)
    for col in board.columns:
        if col.tasks is None:
            col.tasks = []

    return board


def buildBoardFromV2(brainfilePath: str) -> Board:
    dirs = getV2Dirs(brainfilePath)
    board = readV2BoardConfig(brainfilePath)
    task_docs = readTasksDir(dirs.boardDir)

    tasks_by_column: dict[str, list[TaskDocument]] = {}
    for doc in task_docs:
        col_id = doc.task.column or "todo"
        tasks_by_column.setdefault(col_id, []).append(doc)

    for col in board.columns:
        col_docs = tasks_by_column.get(col.id, [])

        def _sort_key(d: TaskDocument) -> tuple[int, str]:
            pos = d.task.position if d.task.position is not None else 2**31 - 1
            return (pos, d.task.id)

        col_docs.sort(key=_sort_key)

        col.tasks = []
        for doc in col_docs:
            task = doc.task.model_copy(deep=True)
            if not task.description:
                desc = extractDescription(doc.body)
                if desc:
                    task.description = desc
            col.tasks.append(task)

    return board
