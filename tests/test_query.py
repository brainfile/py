"""Tests for the query module."""

from datetime import date, datetime

import pytest

from brainfile import (
    Board,
    Column,
    Priority,
    Subtask,
    Task,
    column_exists,
    find_column_by_id,
    find_column_by_name,
    find_task_by_id,
    get_all_tasks,
    get_column_task_count,
    get_overdue_tasks,
    get_tasks_by_assignee,
    get_tasks_by_priority,
    get_tasks_by_tag,
    get_tasks_with_incomplete_subtasks,
    get_total_task_count,
    search_tasks,
    task_id_exists,
)


class TestFindColumnById:
    """Tests for find_column_by_id."""

    def test_find_existing_column(self, board_with_tasks: Board):
        """Test finding an existing column."""
        column = find_column_by_id(board_with_tasks, "todo")
        assert column is not None
        assert column.id == "todo"
        assert column.title == "To Do"

    def test_find_nonexistent_column(self, board_with_tasks: Board):
        """Test finding a non-existent column."""
        column = find_column_by_id(board_with_tasks, "nonexistent")
        assert column is None


class TestFindColumnByName:
    """Tests for find_column_by_name."""

    def test_find_by_name_exact(self, board_with_tasks: Board):
        """Test finding by exact name."""
        column = find_column_by_name(board_with_tasks, "To Do")
        assert column is not None
        assert column.id == "todo"

    def test_find_by_name_case_insensitive(self, board_with_tasks: Board):
        """Test finding by name is case-insensitive."""
        column = find_column_by_name(board_with_tasks, "to do")
        assert column is not None
        assert column.id == "todo"

    def test_find_by_name_nonexistent(self, board_with_tasks: Board):
        """Test finding non-existent name."""
        column = find_column_by_name(board_with_tasks, "Nonexistent")
        assert column is None


class TestFindTaskById:
    """Tests for find_task_by_id."""

    def test_find_existing_task(self, board_with_tasks: Board):
        """Test finding an existing task."""
        task_info = find_task_by_id(board_with_tasks, "task-1")
        assert task_info is not None
        assert task_info.task.id == "task-1"
        assert task_info.task.title == "First Task"
        assert task_info.column.id == "todo"
        assert task_info.index == 0

    def test_find_task_in_different_column(self, board_with_tasks: Board):
        """Test finding a task in a non-first column."""
        task_info = find_task_by_id(board_with_tasks, "task-3")
        assert task_info is not None
        assert task_info.column.id == "in-progress"

    def test_find_nonexistent_task(self, board_with_tasks: Board):
        """Test finding a non-existent task."""
        task_info = find_task_by_id(board_with_tasks, "task-999")
        assert task_info is None


class TestTaskIdExists:
    """Tests for task_id_exists."""

    def test_existing_task(self, board_with_tasks: Board):
        """Test checking existing task ID."""
        assert task_id_exists(board_with_tasks, "task-1") is True
        assert task_id_exists(board_with_tasks, "task-3") is True

    def test_nonexistent_task(self, board_with_tasks: Board):
        """Test checking non-existent task ID."""
        assert task_id_exists(board_with_tasks, "task-999") is False


class TestColumnExists:
    """Tests for column_exists."""

    def test_existing_column(self, board_with_tasks: Board):
        """Test checking existing column."""
        assert column_exists(board_with_tasks, "todo") is True
        assert column_exists(board_with_tasks, "done") is True

    def test_nonexistent_column(self, board_with_tasks: Board):
        """Test checking non-existent column."""
        assert column_exists(board_with_tasks, "nonexistent") is False


class TestGetAllTasks:
    """Tests for get_all_tasks."""

    def test_get_all_tasks(self, board_with_tasks: Board):
        """Test getting all tasks."""
        tasks = get_all_tasks(board_with_tasks)
        assert len(tasks) == 3
        task_ids = [t.id for t in tasks]
        assert "task-1" in task_ids
        assert "task-2" in task_ids
        assert "task-3" in task_ids

    def test_empty_board(self, minimal_board: Board):
        """Test getting tasks from empty board."""
        tasks = get_all_tasks(minimal_board)
        assert len(tasks) == 0


class TestGetTasksByTag:
    """Tests for get_tasks_by_tag."""

    def test_get_tasks_with_tag(self, board_with_tasks: Board):
        """Test getting tasks by tag."""
        tasks = get_tasks_by_tag(board_with_tasks, "urgent")
        assert len(tasks) == 1
        assert tasks[0].id == "task-1"

    def test_nonexistent_tag(self, board_with_tasks: Board):
        """Test getting tasks with non-existent tag."""
        tasks = get_tasks_by_tag(board_with_tasks, "nonexistent")
        assert len(tasks) == 0


class TestGetTasksByPriority:
    """Tests for get_tasks_by_priority."""

    def test_get_high_priority_tasks(self, board_with_tasks: Board):
        """Test getting high priority tasks."""
        tasks = get_tasks_by_priority(board_with_tasks, Priority.HIGH)
        assert len(tasks) == 1
        assert tasks[0].id == "task-1"

    def test_get_priority_by_string(self, board_with_tasks: Board):
        """Test getting tasks by priority string."""
        tasks = get_tasks_by_priority(board_with_tasks, "medium")
        assert len(tasks) == 1
        assert tasks[0].id == "task-2"


class TestGetTasksByAssignee:
    """Tests for get_tasks_by_assignee."""

    def test_get_tasks_by_assignee(self, board_with_tasks: Board):
        """Test getting tasks by assignee."""
        tasks = get_tasks_by_assignee(board_with_tasks, "alice")
        assert len(tasks) == 1
        assert tasks[0].id == "task-3"

    def test_nonexistent_assignee(self, board_with_tasks: Board):
        """Test getting tasks for non-existent assignee."""
        tasks = get_tasks_by_assignee(board_with_tasks, "nonexistent")
        assert len(tasks) == 0


class TestSearchTasks:
    """Tests for search_tasks."""

    def test_search_by_title(self, board_with_tasks: Board):
        """Test searching by title."""
        tasks = search_tasks(board_with_tasks, "First")
        assert len(tasks) == 1
        assert tasks[0].id == "task-1"

    def test_search_by_description(self, board_with_tasks: Board):
        """Test searching by description."""
        tasks = search_tasks(board_with_tasks, "Description 1")
        assert len(tasks) == 1
        assert tasks[0].id == "task-1"

    def test_search_case_insensitive(self, board_with_tasks: Board):
        """Test that search is case-insensitive."""
        tasks = search_tasks(board_with_tasks, "first")
        assert len(tasks) == 1

    def test_search_no_results(self, board_with_tasks: Board):
        """Test search with no results."""
        tasks = search_tasks(board_with_tasks, "nonexistent")
        assert len(tasks) == 0


class TestGetColumnTaskCount:
    """Tests for get_column_task_count."""

    def test_get_count(self, board_with_tasks: Board):
        """Test getting task count for column."""
        assert get_column_task_count(board_with_tasks, "todo") == 2
        assert get_column_task_count(board_with_tasks, "in-progress") == 1
        assert get_column_task_count(board_with_tasks, "done") == 0

    def test_nonexistent_column(self, board_with_tasks: Board):
        """Test getting count for non-existent column."""
        assert get_column_task_count(board_with_tasks, "nonexistent") == 0


class TestGetTotalTaskCount:
    """Tests for get_total_task_count."""

    def test_get_total(self, board_with_tasks: Board):
        """Test getting total task count."""
        assert get_total_task_count(board_with_tasks) == 3

    def test_empty_board(self, minimal_board: Board):
        """Test total count on empty board."""
        assert get_total_task_count(minimal_board) == 0


class TestGetTasksWithIncompleteSubtasks:
    """Tests for get_tasks_with_incomplete_subtasks."""

    def test_find_tasks_with_incomplete(self, board_with_subtasks: Board):
        """Test finding tasks with incomplete subtasks."""
        tasks = get_tasks_with_incomplete_subtasks(board_with_subtasks)
        assert len(tasks) == 1
        assert tasks[0].id == "task-1"

    def test_no_incomplete_subtasks(self):
        """Test when all subtasks are complete."""
        board = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[
                        Task(
                            id="task-1",
                            title="Task",
                            subtasks=[
                                Subtask(id="task-1-1", title="Sub", completed=True),
                            ],
                        ),
                    ],
                ),
            ],
        )
        tasks = get_tasks_with_incomplete_subtasks(board)
        assert len(tasks) == 0


class TestGetOverdueTasks:
    """Tests for get_overdue_tasks."""

    def test_find_overdue_tasks(self):
        """Test finding overdue tasks."""
        board = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[
                        Task(id="task-1", title="Overdue", due_date="2020-01-01"),
                        Task(id="task-2", title="Future", due_date="2030-12-31"),
                        Task(id="task-3", title="No due date"),
                    ],
                ),
            ],
        )
        tasks = get_overdue_tasks(board, date(2024, 1, 1))
        assert len(tasks) == 1
        assert tasks[0].id == "task-1"

    def test_no_overdue_tasks(self):
        """Test when no tasks are overdue."""
        board = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[
                        Task(id="task-1", title="Future", due_date="2030-12-31"),
                    ],
                ),
            ],
        )
        tasks = get_overdue_tasks(board, date(2024, 1, 1))
        assert len(tasks) == 0
