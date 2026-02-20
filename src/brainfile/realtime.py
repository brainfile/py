"""
Realtime utilities for diffing and hashing brainfiles.

This module provides utilities for detecting changes between board states,
useful for real-time collaboration and change tracking.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .models import Board, Column, Task
from .serializer import BrainfileSerializer


@dataclass
class ColumnDiff:
    """Diff information for a column."""

    column_id: str
    before: Column | None = None
    after: Column | None = None
    from_index: int | None = None
    to_index: int | None = None
    changed_fields: list[str] | None = None


@dataclass
class TaskDiff:
    """Diff information for a task."""

    task_id: str
    before: Task | None = None
    after: Task | None = None
    from_column_id: str | None = None
    to_column_id: str | None = None
    from_index: int | None = None
    to_index: int | None = None
    changed_fields: list[str] | None = None


@dataclass
class BoardDiff:
    """Complete diff between two board states."""

    metadata_changed: bool = False
    columns_added: list[ColumnDiff] = field(default_factory=list)
    columns_removed: list[ColumnDiff] = field(default_factory=list)
    columns_updated: list[ColumnDiff] = field(default_factory=list)
    columns_moved: list[ColumnDiff] = field(default_factory=list)
    tasks_added: list[TaskDiff] = field(default_factory=list)
    tasks_removed: list[TaskDiff] = field(default_factory=list)
    tasks_updated: list[TaskDiff] = field(default_factory=list)
    tasks_moved: list[TaskDiff] = field(default_factory=list)


def hash_board_content(content: str) -> str:
    """
    Generate a stable hash for raw Brainfile content.

    Uses SHA-256 for collision resistance and cross-process consistency.

    Args:
        content: The raw brainfile content string

    Returns:
        SHA-256 hash as hex string
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def hash_board(board: Board) -> str:
    """
    Generate a stable hash for a Board by serializing with BrainfileSerializer.

    Args:
        board: The board to hash

    Returns:
        SHA-256 hash as hex string
    """
    serialized = BrainfileSerializer.serialize(board)
    return hash_board_content(serialized)


def _is_equal(a: object, b: object) -> bool:
    """Compare two objects for equality using JSON serialization."""
    try:
        return json.dumps(a, sort_keys=True, default=str) == json.dumps(
            b, sort_keys=True, default=str
        )
    except (TypeError, ValueError):
        return a == b


def _index_columns(
    columns: list[Column],
) -> dict[str, tuple[Column, int]]:
    """Create an index of columns by ID."""
    return {col.id: (col, index) for index, col in enumerate(columns)}


def _index_tasks(
    columns: list[Column],
) -> dict[str, tuple[Task, str, int]]:
    """Create an index of tasks by ID, including column ID and index."""
    result: dict[str, tuple[Task, str, int]] = {}
    for col in columns:
        for index, task in enumerate(col.tasks):
            result[task.id] = (task, col.id, index)
    return result


def _detect_changed_fields(
    before: object,
    after: object,
    fields: list[str],
) -> list[str]:
    """Detect which fields have changed between two objects."""
    changed: list[str] = []

    for field_name in fields:
        before_value = getattr(before, field_name, None)
        after_value = getattr(after, field_name, None)

        if not _is_equal(before_value, after_value):
            changed.append(field_name)

    return changed


def _get_metadata(board: Board) -> dict[str, object]:
    """Extract metadata fields from a board."""
    return {
        "title": board.title,
        "protocol_version": board.protocol_version,
        "schema_url": board.schema_url,
        "agent": board.agent,
        "rules": board.rules,
        "stats_config": board.stats_config,
    }


def diff_boards(previous: Board, next_board: Board) -> BoardDiff:
    """
    Compute a structural diff between two Board objects.

    Args:
        previous: The previous board state
        next_board: The next board state

    Returns:
        BoardDiff with all detected changes
    """
    # Check metadata changes
    prev_metadata = _get_metadata(previous)
    next_metadata = _get_metadata(next_board)
    metadata_changed = not _is_equal(prev_metadata, next_metadata)

    # Index columns
    column_id_to_prev = _index_columns(previous.columns)
    column_id_to_next = _index_columns(next_board.columns)

    columns_added: list[ColumnDiff] = []
    columns_removed: list[ColumnDiff] = []
    columns_updated: list[ColumnDiff] = []
    columns_moved: list[ColumnDiff] = []

    # Find removed columns
    for col_id, (prev_col, prev_index) in column_id_to_prev.items():
        if col_id not in column_id_to_next:
            columns_removed.append(
                ColumnDiff(
                    column_id=col_id,
                    before=prev_col,
                    from_index=prev_index,
                )
            )

    # Find added, updated, and moved columns
    for col_id, (next_col, next_index) in column_id_to_next.items():
        if col_id not in column_id_to_prev:
            columns_added.append(
                ColumnDiff(
                    column_id=col_id,
                    after=next_col,
                    to_index=next_index,
                )
            )
            continue

        prev_col, prev_index = column_id_to_prev[col_id]

        # Check for field changes
        changed_fields = _detect_changed_fields(prev_col, next_col, ["title", "order"])
        if changed_fields:
            columns_updated.append(
                ColumnDiff(
                    column_id=col_id,
                    before=prev_col,
                    after=next_col,
                    changed_fields=changed_fields,
                )
            )

        # Check for position changes
        if prev_index != next_index:
            columns_moved.append(
                ColumnDiff(
                    column_id=col_id,
                    before=prev_col,
                    after=next_col,
                    from_index=prev_index,
                    to_index=next_index,
                )
            )

    # Index tasks
    prev_tasks = _index_tasks(previous.columns)
    next_tasks = _index_tasks(next_board.columns)

    tasks_added: list[TaskDiff] = []
    tasks_removed: list[TaskDiff] = []
    tasks_updated: list[TaskDiff] = []
    tasks_moved: list[TaskDiff] = []

    # Find removed tasks
    for task_id, (prev_task, prev_col_id, prev_index) in prev_tasks.items():
        if task_id not in next_tasks:
            tasks_removed.append(
                TaskDiff(
                    task_id=task_id,
                    before=prev_task,
                    from_column_id=prev_col_id,
                    from_index=prev_index,
                )
            )

    # Find added, updated, and moved tasks
    for task_id, (next_task, next_col_id, next_index) in next_tasks.items():
        if task_id not in prev_tasks:
            tasks_added.append(
                TaskDiff(
                    task_id=task_id,
                    after=next_task,
                    to_column_id=next_col_id,
                    to_index=next_index,
                )
            )
            continue

        prev_task, prev_col_id, prev_index = prev_tasks[task_id]

        # Check for position changes
        moved = prev_col_id != next_col_id or prev_index != next_index
        if moved:
            tasks_moved.append(
                TaskDiff(
                    task_id=task_id,
                    before=prev_task,
                    after=next_task,
                    from_column_id=prev_col_id,
                    to_column_id=next_col_id,
                    from_index=prev_index,
                    to_index=next_index,
                )
            )

        # Check for field changes
        changed_fields = _detect_changed_fields(
            prev_task,
            next_task,
            [
                "title",
                "description",
                "related_files",
                "assignee",
                "tags",
                "priority",
                "due_date",
                "subtasks",
                "template",
            ],
        )
        if changed_fields:
            tasks_updated.append(
                TaskDiff(
                    task_id=task_id,
                    before=prev_task,
                    after=next_task,
                    from_column_id=prev_col_id,
                    to_column_id=next_col_id,
                    from_index=prev_index,
                    to_index=next_index,
                    changed_fields=changed_fields,
                )
            )

    return BoardDiff(
        metadata_changed=metadata_changed,
        columns_added=columns_added,
        columns_removed=columns_removed,
        columns_updated=columns_updated,
        columns_moved=columns_moved,
        tasks_added=tasks_added,
        tasks_removed=tasks_removed,
        tasks_updated=tasks_updated,
        tasks_moved=tasks_moved,
    )
