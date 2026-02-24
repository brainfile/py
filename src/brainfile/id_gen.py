"""
ID generation utilities for tasks and other entities.

This module provides functions for generating and validating task and
subtask IDs in the brainfile format.
"""

from __future__ import annotations

import re

from .models import Board

DEFAULT_PREFIX = "task"


def extract_task_id_number(task_id: str, prefix: str = DEFAULT_PREFIX) -> int:
    """
    Extract numeric ID from task ID string.

    Args:
        task_id: Task ID like "task-123", "task-42-1", or "epic-5"
        prefix: Prefix to match (default: "task")

    Returns:
        Numeric portion or 0 if not parseable
    """
    escaped = re.escape(prefix)
    match = re.search(rf"{escaped}-(\d+)", task_id)
    return int(match.group(1)) if match else 0


def get_max_task_id_number(board: Board) -> int:
    """
    Get the highest task ID number from active tasks in a board.

    Scans all columns for tasks and extracts the maximum numeric ID.
    Does NOT check archive - this matches TypeScript behavior exactly.

    Args:
        board: Board to scan

    Returns:
        Highest task ID number found in active columns, or 0 if no tasks
    """
    all_task_ids = [
        extract_task_id_number(task.id) for col in board.columns for task in col.tasks
    ]

    # Note: DO NOT check board.archive - match TypeScript behavior exactly
    # Archived tasks are not considered when generating new task IDs

    return max(all_task_ids) if all_task_ids else 0


def generate_next_task_id(board: Board) -> str:
    """
    Generate the next task ID for a board.

    Args:
        board: Board to generate ID for

    Returns:
        Next task ID like "task-42"
    """
    max_id = get_max_task_id_number(board)
    return f"task-{max_id + 1}"


def generate_subtask_id(task_id: str, index: int) -> str:
    """
    Generate a subtask ID based on a task ID and index.

    Args:
        task_id: Parent task ID
        index: Subtask index (1-based)

    Returns:
        Subtask ID like "task-42-1"
    """
    return f"{task_id}-{index}"


def generate_next_subtask_id(task_id: str, existing_subtask_ids: list[str]) -> str:
    """
    Generate the next subtask ID for a task.

    Args:
        task_id: Parent task ID
        existing_subtask_ids: Array of existing subtask IDs

    Returns:
        Next subtask ID
    """
    indices: list[int] = []

    for subtask_id in existing_subtask_ids:
        pattern = rf"{re.escape(task_id)}-(\d+)"
        match = re.match(pattern, subtask_id)
        if match:
            index = int(match.group(1))
            if index > 0:
                indices.append(index)

    max_index = max(indices) if indices else 0
    return generate_subtask_id(task_id, max_index + 1)


def is_valid_task_id(task_id: str, prefix: str = DEFAULT_PREFIX) -> bool:
    """
    Validate task ID format.

    Args:
        task_id: Task ID to validate
        prefix: Prefix to match (default: "task")

    Returns:
        True if valid format ({prefix}-N)
    """
    escaped = re.escape(prefix)
    return bool(re.match(rf"^{escaped}-\d+$", task_id))


def is_valid_subtask_id(subtask_id: str, prefix: str = DEFAULT_PREFIX) -> bool:
    """
    Validate subtask ID format.

    Args:
        subtask_id: Subtask ID to validate
        prefix: Prefix to match (default: "task")

    Returns:
        True if valid format ({prefix}-N-M)
    """
    escaped = re.escape(prefix)
    return bool(re.match(rf"^{escaped}-\d+-\d+$", subtask_id))


def get_parent_task_id(subtask_id: str, prefix: str = DEFAULT_PREFIX) -> str | None:
    """
    Extract parent task ID from subtask ID.

    Args:
        subtask_id: Subtask ID like "task-42-1" or "epic-3-2"
        prefix: Prefix to match (default: "task")

    Returns:
        Parent task ID like "{prefix}-42", or None if invalid
    """
    escaped = re.escape(prefix)
    match = re.match(rf"^({escaped}-\d+)-\d+$", subtask_id)
    return match.group(1) if match else None
