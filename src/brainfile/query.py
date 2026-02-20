"""
Query and finder functions for boards.

These are pure read-only functions that don't modify the board.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .models import Board, Column, Priority, Task


@dataclass
class TaskInfo:
    """Information about a task's location in the board."""

    task: Task
    """The task object"""

    column: Column
    """The column containing the task"""

    index: int
    """The index of the task within the column"""


def find_column_by_id(board: Board, column_id: str) -> Column | None:
    """
    Find a column by ID.

    Args:
        board: Board to search
        column_id: Column ID to find

    Returns:
        Column or None if not found
    """
    for column in board.columns:
        if column.id == column_id:
            return column
    return None


def find_column_by_name(board: Board, title: str) -> Column | None:
    """
    Find a column by title (case-insensitive).

    Args:
        board: Board to search
        title: Column title to find

    Returns:
        Column or None if not found
    """
    normalized_title = title.lower()
    for column in board.columns:
        if column.title.lower() == normalized_title:
            return column
    return None


def find_task_by_id(board: Board, task_id: str) -> TaskInfo | None:
    """
    Find a task by ID across all columns.

    Args:
        board: Board to search
        task_id: Task ID to find

    Returns:
        TaskInfo with task, column, and index, or None if not found
    """
    for column in board.columns:
        for index, task in enumerate(column.tasks):
            if task.id == task_id:
                return TaskInfo(task=task, column=column, index=index)
    return None


def task_id_exists(board: Board, task_id: str) -> bool:
    """
    Check if a task ID already exists in a board.

    Args:
        board: Board to check
        task_id: Task ID to look for

    Returns:
        True if task ID exists
    """
    for column in board.columns:
        for task in column.tasks:
            if task.id == task_id:
                return True
    return False


def column_exists(board: Board, column_id: str) -> bool:
    """
    Check if a column exists.

    Args:
        board: Board to check
        column_id: Column ID to look for

    Returns:
        True if column exists
    """
    return any(column.id == column_id for column in board.columns)


def get_all_tasks(board: Board) -> list[Task]:
    """
    Get all tasks from a board (across all columns).

    Args:
        board: Board to query

    Returns:
        Array of all tasks
    """
    tasks: list[Task] = []
    for column in board.columns:
        tasks.extend(column.tasks)
    return tasks


def get_tasks_by_tag(board: Board, tag: str) -> list[Task]:
    """
    Get tasks by tag.

    Args:
        board: Board to query
        tag: Tag to filter by

    Returns:
        Array of tasks with the specified tag
    """
    return [task for task in get_all_tasks(board) if task.tags and tag in task.tags]


def get_tasks_by_priority(board: Board, priority: Priority | str) -> list[Task]:
    """
    Get tasks by priority.

    Args:
        board: Board to query
        priority: Priority level to filter by

    Returns:
        Array of tasks with the specified priority
    """
    priority_value = priority.value if isinstance(priority, Priority) else priority
    return [
        task
        for task in get_all_tasks(board)
        if task.priority and task.priority.value == priority_value
    ]


def get_tasks_by_assignee(board: Board, assignee: str) -> list[Task]:
    """
    Get tasks by assignee.

    Args:
        board: Board to query
        assignee: Assignee name to filter by

    Returns:
        Array of tasks assigned to the specified person
    """
    return [task for task in get_all_tasks(board) if task.assignee == assignee]


def search_tasks(board: Board, query: str) -> list[Task]:
    """
    Search tasks by title or description (case-insensitive).

    Args:
        board: Board to search
        query: Search query string

    Returns:
        Array of tasks matching the query
    """
    normalized_query = query.lower()
    results: list[Task] = []

    for task in get_all_tasks(board):
        if normalized_query in task.title.lower():
            results.append(task)
        elif task.description and normalized_query in task.description.lower():
            results.append(task)

    return results


def get_column_task_count(board: Board, column_id: str) -> int:
    """
    Get task count for a column.

    Args:
        board: Board to query
        column_id: Column ID

    Returns:
        Number of tasks in the column, or 0 if column not found
    """
    column = find_column_by_id(board, column_id)
    return len(column.tasks) if column else 0


def get_total_task_count(board: Board) -> int:
    """
    Get total task count across all columns.

    Args:
        board: Board to query

    Returns:
        Total number of tasks
    """
    return sum(len(column.tasks) for column in board.columns)


def get_tasks_with_incomplete_subtasks(board: Board) -> list[Task]:
    """
    Find tasks with incomplete subtasks.

    Args:
        board: Board to query

    Returns:
        Array of tasks that have at least one incomplete subtask
    """
    return [
        task
        for task in get_all_tasks(board)
        if task.subtasks and any(not subtask.completed for subtask in task.subtasks)
    ]


def get_overdue_tasks(
    board: Board,
    current_date: date | datetime | None = None,
) -> list[Task]:
    """
    Find overdue tasks.

    Args:
        board: Board to query
        current_date: Current date to compare against (defaults to today)

    Returns:
        Array of tasks past their due date
    """
    if current_date is None:
        current_date = datetime.now()

    if isinstance(current_date, datetime):
        current_date = current_date.date()

    results: list[Task] = []

    for task in get_all_tasks(board):
        if not task.due_date:
            continue

        try:
            # Parse ISO date string (YYYY-MM-DD)
            due_date = datetime.fromisoformat(task.due_date.split("T")[0]).date()
            if due_date < current_date:
                results.append(task)
        except ValueError:
            # Skip tasks with invalid date formats
            continue

    return results
