"""Tests for the id_gen module."""

import pytest

from brainfile import (
    extract_task_id_number,
    generate_next_subtask_id,
    generate_subtask_id,
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

    def test_extract_subtask_id(self):
        """Test extracting from valid subtask IDs."""
        assert extract_task_id_number("task-42-1") == 42
        assert extract_task_id_number("task-5-10") == 5

    def test_extract_with_custom_prefix(self):
        """Test extracting with custom prefix."""
        assert extract_task_id_number("epic-7", "epic") == 7
        assert extract_task_id_number("epic-9-2", "epic") == 9
        assert extract_task_id_number("task-9", "epic") == 0

    def test_extract_with_escaped_prefix(self):
        """Test extracting with prefixes containing regex chars."""
        assert extract_task_id_number("type.v2-11", "type.v2") == 11


class TestGenerateSubtaskId:
    """Tests for generate_subtask_id (0-indexed, output is 1-based)."""

    def test_generate_subtask_id(self):
        """Test generating subtask ID from index."""
        assert generate_subtask_id("task-1", 0) == "task-1-1"
        assert generate_subtask_id("task-42", 2) == "task-42-3"


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

    def test_custom_prefix(self):
        """Test task ID validation with custom prefix."""
        assert is_valid_task_id("epic-1", "epic") is True
        assert is_valid_task_id("epic-123", "epic") is True
        assert is_valid_task_id("task-1", "epic") is False

    def test_custom_prefix_with_regex_chars(self):
        """Test task ID validation with escaped custom prefix."""
        assert is_valid_task_id("type.v2-1", "type.v2") is True
        assert is_valid_task_id("typeXv2-1", "type.v2") is False


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

    def test_custom_prefix(self):
        """Test subtask ID validation with custom prefix."""
        assert is_valid_subtask_id("epic-1-1", "epic") is True
        assert is_valid_subtask_id("epic-123-456", "epic") is True
        assert is_valid_subtask_id("task-1-1", "epic") is False

    def test_custom_prefix_with_regex_chars(self):
        """Test subtask ID validation with escaped custom prefix."""
        assert is_valid_subtask_id("type.v2-1-1", "type.v2") is True
        assert is_valid_subtask_id("typeXv2-1-1", "type.v2") is False


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

    def test_custom_prefix(self):
        """Test extracting parent with custom prefix."""
        assert get_parent_task_id("epic-1-1", "epic") == "epic-1"
        assert get_parent_task_id("epic-42-5", "epic") == "epic-42"
        assert get_parent_task_id("task-1-1", "epic") is None

    def test_custom_prefix_with_regex_chars(self):
        """Test extracting parent with escaped custom prefix."""
        assert get_parent_task_id("type.v2-8-3", "type.v2") == "type.v2-8"
