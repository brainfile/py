"""Tests for the validator module."""

import pytest

from brainfile import (
    Board,
    BrainfileValidator,
    Column,
    Priority,
    Subtask,
    Task,
    ValidationResult,
)


class TestValidateBoard:
    """Tests for validate (Board validation)."""

    def test_validate_minimal_board(self, minimal_board: Board):
        """Test validating a minimal valid board."""
        result = BrainfileValidator.validate(minimal_board)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_complex_board(self, complex_board: Board):
        """Test validating a complex valid board."""
        result = BrainfileValidator.validate(complex_board)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_null_board(self):
        """Test validating null board."""
        result = BrainfileValidator.validate(None)
        assert result.valid is False
        assert any("null" in e.message.lower() for e in result.errors)

    def test_validate_empty_title(self):
        """Test validating board with empty title."""
        board = {"title": "", "columns": []}
        result = BrainfileValidator.validate(board)
        assert result.valid is False
        assert any("title" in e.path for e in result.errors)

    def test_validate_missing_columns(self):
        """Test validating board without columns."""
        board = {"title": "Test"}
        result = BrainfileValidator.validate(board)
        assert result.valid is False
        assert any("columns" in e.path for e in result.errors)

    def test_validate_columns_not_array(self):
        """Test validating board with non-array columns."""
        board = {"title": "Test", "columns": "not an array"}
        result = BrainfileValidator.validate(board)
        assert result.valid is False
        assert any("columns" in e.path and "array" in e.message.lower() for e in result.errors)


class TestValidateColumn:
    """Tests for validate_column."""

    def test_validate_valid_column(self):
        """Test validating a valid column."""
        column = {"id": "todo", "title": "To Do", "tasks": []}
        errors = BrainfileValidator.validate_column(column, "columns[0]")
        assert len(errors) == 0

    def test_validate_null_column(self):
        """Test validating null column."""
        errors = BrainfileValidator.validate_column(None, "columns[0]")
        assert len(errors) == 1
        assert "null" in errors[0].message.lower()

    def test_validate_missing_column_id(self):
        """Test validating column without id."""
        column = {"title": "To Do", "tasks": []}
        errors = BrainfileValidator.validate_column(column, "columns[0]")
        assert any("id" in e.path for e in errors)

    def test_validate_empty_column_id(self):
        """Test validating column with empty id."""
        column = {"id": "", "title": "To Do", "tasks": []}
        errors = BrainfileValidator.validate_column(column, "columns[0]")
        assert any("id" in e.path for e in errors)

    def test_validate_missing_column_title(self):
        """Test validating column without title."""
        column = {"id": "todo", "tasks": []}
        errors = BrainfileValidator.validate_column(column, "columns[0]")
        assert any("title" in e.path for e in errors)

    def test_validate_missing_tasks(self):
        """Test validating column without tasks."""
        column = {"id": "todo", "title": "To Do"}
        errors = BrainfileValidator.validate_column(column, "columns[0]")
        assert any("tasks" in e.path for e in errors)

    def test_validate_tasks_not_array(self):
        """Test validating column with non-array tasks."""
        column = {"id": "todo", "title": "To Do", "tasks": "not an array"}
        errors = BrainfileValidator.validate_column(column, "columns[0]")
        assert any("tasks" in e.path and "array" in e.message.lower() for e in errors)


class TestValidateTask:
    """Tests for validate_task."""

    def test_validate_valid_task(self):
        """Test validating a valid task."""
        task = {"id": "task-1", "title": "Test Task"}
        errors = BrainfileValidator.validate_task(task, "tasks[0]")
        assert len(errors) == 0

    def test_validate_null_task(self):
        """Test validating null task."""
        errors = BrainfileValidator.validate_task(None, "tasks[0]")
        assert len(errors) == 1
        assert "null" in errors[0].message.lower()

    def test_validate_missing_task_id(self):
        """Test validating task without id."""
        task = {"title": "Test Task"}
        errors = BrainfileValidator.validate_task(task, "tasks[0]")
        assert any("id" in e.path for e in errors)

    def test_validate_missing_task_title(self):
        """Test validating task without title."""
        task = {"id": "task-1"}
        errors = BrainfileValidator.validate_task(task, "tasks[0]")
        assert any("title" in e.path for e in errors)

    def test_validate_invalid_priority(self):
        """Test validating task with invalid priority."""
        task = {"id": "task-1", "title": "Test Task", "priority": "invalid"}
        errors = BrainfileValidator.validate_task(task, "tasks[0]")
        assert any("priority" in e.path for e in errors)

    def test_validate_valid_priority(self):
        """Test validating task with valid priority."""
        task = {"id": "task-1", "title": "Test Task", "priority": "high"}
        errors = BrainfileValidator.validate_task(task, "tasks[0]")
        assert not any("priority" in e.path for e in errors)

    def test_validate_invalid_template(self):
        """Test validating task with invalid template."""
        task = {"id": "task-1", "title": "Test Task", "template": "invalid"}
        errors = BrainfileValidator.validate_task(task, "tasks[0]")
        assert any("template" in e.path for e in errors)

    def test_validate_tags_not_array(self):
        """Test validating task with non-array tags."""
        task = {"id": "task-1", "title": "Test Task", "tags": "not an array"}
        errors = BrainfileValidator.validate_task(task, "tasks[0]")
        assert any("tags" in e.path for e in errors)

    def test_validate_related_files_not_array(self):
        """Test validating task with non-array relatedFiles."""
        task = {"id": "task-1", "title": "Test Task", "relatedFiles": "not an array"}
        errors = BrainfileValidator.validate_task(task, "tasks[0]")
        assert any("relatedFiles" in e.path for e in errors)

    def test_validate_subtasks_not_array(self):
        """Test validating task with non-array subtasks."""
        task = {"id": "task-1", "title": "Test Task", "subtasks": "not an array"}
        errors = BrainfileValidator.validate_task(task, "tasks[0]")
        assert any("subtasks" in e.path for e in errors)


class TestValidateSubtask:
    """Tests for validate_subtask."""

    def test_validate_valid_subtask(self):
        """Test validating a valid subtask."""
        subtask = {"id": "task-1-1", "title": "Subtask", "completed": False}
        errors = BrainfileValidator.validate_subtask(subtask, "subtasks[0]")
        assert len(errors) == 0

    def test_validate_null_subtask(self):
        """Test validating null subtask."""
        errors = BrainfileValidator.validate_subtask(None, "subtasks[0]")
        assert len(errors) == 1
        assert "null" in errors[0].message.lower()

    def test_validate_missing_subtask_id(self):
        """Test validating subtask without id."""
        subtask = {"title": "Subtask", "completed": False}
        errors = BrainfileValidator.validate_subtask(subtask, "subtasks[0]")
        assert any("id" in e.path for e in errors)

    def test_validate_missing_subtask_title(self):
        """Test validating subtask without title."""
        subtask = {"id": "task-1-1", "completed": False}
        errors = BrainfileValidator.validate_subtask(subtask, "subtasks[0]")
        assert any("title" in e.path for e in errors)

    def test_validate_missing_completed(self):
        """Test validating subtask without completed."""
        subtask = {"id": "task-1-1", "title": "Subtask"}
        errors = BrainfileValidator.validate_subtask(subtask, "subtasks[0]")
        assert any("completed" in e.path for e in errors)

    def test_validate_completed_not_boolean(self):
        """Test validating subtask with non-boolean completed."""
        subtask = {"id": "task-1-1", "title": "Subtask", "completed": "yes"}
        errors = BrainfileValidator.validate_subtask(subtask, "subtasks[0]")
        assert any("completed" in e.path and "boolean" in e.message.lower() for e in errors)


class TestValidateRules:
    """Tests for validate_rules."""

    def test_validate_valid_rules(self):
        """Test validating valid rules."""
        rules = {
            "always": [{"id": 1, "rule": "Always test"}],
            "never": [{"id": 2, "rule": "Never skip tests"}],
        }
        errors = BrainfileValidator.validate_rules(rules, "rules")
        assert len(errors) == 0

    def test_validate_null_rules(self):
        """Test validating null rules."""
        errors = BrainfileValidator.validate_rules(None, "rules")
        assert len(errors) == 1
        assert "null" in errors[0].message.lower()

    def test_validate_rules_not_array(self):
        """Test validating rules with non-array rule list."""
        rules = {"always": "not an array"}
        errors = BrainfileValidator.validate_rules(rules, "rules")
        assert any("always" in e.path and "array" in e.message.lower() for e in errors)


class TestValidateRule:
    """Tests for validate_rule."""

    def test_validate_valid_rule(self):
        """Test validating a valid rule."""
        rule = {"id": 1, "rule": "Always test"}
        errors = BrainfileValidator.validate_rule(rule, "rules.always[0]")
        assert len(errors) == 0

    def test_validate_null_rule(self):
        """Test validating null rule."""
        errors = BrainfileValidator.validate_rule(None, "rules.always[0]")
        assert len(errors) == 1
        assert "null" in errors[0].message.lower()

    def test_validate_missing_rule_id(self):
        """Test validating rule without id."""
        rule = {"rule": "Always test"}
        errors = BrainfileValidator.validate_rule(rule, "rules.always[0]")
        assert any("id" in e.path for e in errors)

    def test_validate_rule_id_not_number(self):
        """Test validating rule with non-number id."""
        rule = {"id": "not a number", "rule": "Always test"}
        errors = BrainfileValidator.validate_rule(rule, "rules.always[0]")
        assert any("id" in e.path and "number" in e.message.lower() for e in errors)

    def test_validate_missing_rule_text(self):
        """Test validating rule without rule text."""
        rule = {"id": 1}
        errors = BrainfileValidator.validate_rule(rule, "rules.always[0]")
        assert any("rule" in e.path for e in errors)


class TestValidateStatsConfig:
    """Tests for stats config validation."""

    def test_validate_valid_stats_config(self):
        """Test validating board with valid stats config."""
        board = {
            "title": "Test",
            "columns": [],
            "statsConfig": {"columns": ["todo", "done"]},
        }
        result = BrainfileValidator.validate(board)
        assert result.valid is True

    def test_validate_stats_config_too_many_columns(self):
        """Test validating stats config with more than 4 columns."""
        board = {
            "title": "Test",
            "columns": [],
            "statsConfig": {"columns": ["a", "b", "c", "d", "e"]},
        }
        result = BrainfileValidator.validate(board)
        assert result.valid is False
        assert any("statsConfig" in e.path and "4" in e.message for e in result.errors)


class TestValidateBrainfile:
    """Tests for validate_brainfile (type detection + validation)."""

    def test_validate_board_type(self, minimal_board_dict: dict):
        """Test validating and detecting board type."""
        result = BrainfileValidator.validate_brainfile(minimal_board_dict)
        assert result.valid is True
        assert result.type == "board"

    def test_validate_null_data(self):
        """Test validating null data."""
        result = BrainfileValidator.validate_brainfile(None)
        assert result.valid is False
        assert any("null" in e.message.lower() for e in result.errors)

    def test_validate_unknown_type(self):
        """Test validating data with unknown type (non-board) passes type detection."""
        # Note: Journal and other types are community extensions
        # They are detected but not validated by official library
        data = {
            "title": "My Custom Type",
            "type": "custom",
            "items": [],
        }
        result = BrainfileValidator.validate_brainfile(data)
        # Type is detected
        assert result.type == "custom"
        # But validation may not apply board-specific rules
