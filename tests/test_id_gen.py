"""Tests for the id_gen module."""

import pytest

from brainfile import (
    Board,
    Column,
    Task,
    extract_task_id_number,
    generate_next_subtask_id,
    generate_next_task_id,
    generate_subtask_id_from_index,
    get_max_task_id_number,
    get_parent_task_id,
    is_valid_subtask_id,
    is_valid_task_id,
)


class TestExtractTaskIdNumber:
    """Tests for extract_task_id_number."""

    def test_extract_valid_id(self):
        """Test extracting number from valid task ID."""
        assert extract_task_id_number("task-123") == 123
        assert extract_task_id_number("task-1") == 1
        assert extract_task_id_number("task-0") == 0

    def test_extract_invalid_id(self):
        """Test extracting from invalid task ID returns 0."""
        assert extract_task_id_number("invalid") == 0
        assert extract_task_id_number("") == 0
        assert extract_task_id_number("task-") == 0


class TestGetMaxTaskIdNumber:
    """Tests for get_max_task_id_number."""

    def test_empty_board(self, minimal_board: Board):
        """Test max ID on empty board is 0."""
        assert get_max_task_id_number(minimal_board) == 0

    def test_board_with_tasks(self, board_with_tasks: Board):
        """Test max ID with existing tasks."""
        assert get_max_task_id_number(board_with_tasks) == 3

    def test_board_with_archive(self):
        """Test max ID does NOT consider archived tasks (matches TypeScript)."""
        board = Board(
            title="Test",
            columns=[
                Column(id="todo", title="To Do", tasks=[
                    Task(id="task-5", title="Active"),
                ]),
            ],
            archive=[
                Task(id="task-10", title="Archived"),
            ],
        )
        # Archive is NOT checked - this matches TypeScript behavior
        # Only active tasks in columns are considered
        assert get_max_task_id_number(board) == 5


class TestGenerateNextTaskId:
    """Tests for generate_next_task_id."""

    def test_empty_board(self, minimal_board: Board):
        """Test generating ID for empty board."""
        assert generate_next_task_id(minimal_board) == "task-1"

    def test_board_with_tasks(self, board_with_tasks: Board):
        """Test generating next ID."""
        assert generate_next_task_id(board_with_tasks) == "task-4"


class TestGenerateSubtaskId:
    """Tests for generate_subtask_id_from_index."""

    def test_generate_subtask_id(self):
        """Test generating subtask ID from index."""
        assert generate_subtask_id_from_index("task-1", 1) == "task-1-1"
        assert generate_subtask_id_from_index("task-42", 3) == "task-42-3"


class TestGenerateNextSubtaskId:
    """Tests for generate_next_subtask_id."""

    def test_no_existing_subtasks(self):
        """Test generating first subtask ID."""
        assert generate_next_subtask_id("task-1", []) == "task-1-1"

    def test_with_existing_subtasks(self):
        """Test generating next subtask ID."""
        existing = ["task-1-1", "task-1-2", "task-1-3"]
        assert generate_next_subtask_id("task-1", existing) == "task-1-4"

    def test_with_gaps(self):
        """Test generating ID when there are gaps in existing IDs."""
        existing = ["task-1-1", "task-1-5"]
        assert generate_next_subtask_id("task-1", existing) == "task-1-6"


class TestIsValidTaskId:
    """Tests for is_valid_task_id."""

    def test_valid_ids(self):
        """Test valid task IDs."""
        assert is_valid_task_id("task-1") is True
        assert is_valid_task_id("task-123") is True
        assert is_valid_task_id("task-0") is True

    def test_invalid_ids(self):
        """Test invalid task IDs."""
        assert is_valid_task_id("task-") is False
        assert is_valid_task_id("task") is False
        assert is_valid_task_id("") is False
        assert is_valid_task_id("task-abc") is False
        assert is_valid_task_id("task-1-1") is False  # This is a subtask ID


class TestIsValidSubtaskId:
    """Tests for is_valid_subtask_id."""

    def test_valid_ids(self):
        """Test valid subtask IDs."""
        assert is_valid_subtask_id("task-1-1") is True
        assert is_valid_subtask_id("task-123-456") is True

    def test_invalid_ids(self):
        """Test invalid subtask IDs."""
        assert is_valid_subtask_id("task-1") is False  # This is a task ID
        assert is_valid_subtask_id("task-1-") is False
        assert is_valid_subtask_id("") is False


class TestGetParentTaskId:
    """Tests for get_parent_task_id."""

    def test_valid_subtask_id(self):
        """Test extracting parent from valid subtask ID."""
        assert get_parent_task_id("task-1-1") == "task-1"
        assert get_parent_task_id("task-42-5") == "task-42"

    def test_invalid_subtask_id(self):
        """Test extracting parent from invalid subtask ID."""
        assert get_parent_task_id("task-1") is None
        assert get_parent_task_id("invalid") is None
        assert get_parent_task_id("") is None
