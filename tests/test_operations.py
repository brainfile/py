"""Tests for the operations module."""

import pytest

from brainfile import (
    Board,
    Column,
    Priority,
    Subtask,
    Task,
    TaskInput,
    TaskPatch,
    add_subtask,
    add_task,
    archive_task,
    archive_tasks,
    delete_subtask,
    delete_task,
    delete_tasks,
    move_task,
    move_tasks,
    patch_task,
    patch_tasks,
    restore_task,
    set_all_subtasks_completed,
    set_subtasks_completed,
    toggle_subtask,
    update_board_title,
    update_stats_config,
    update_subtask,
    update_task,
)


class TestMoveTask:
    """Tests for move_task."""

    def test_move_task_between_columns(self, board_with_tasks: Board):
        """Test moving a task between columns."""
        result = move_task(board_with_tasks, "task-1", "todo", "in-progress", 0)
        assert result.success is True
        assert result.board is not None
        # Task should be in new column
        in_progress = next(c for c in result.board.columns if c.id == "in-progress")
        assert any(t.id == "task-1" for t in in_progress.tasks)
        # Task should not be in old column
        todo = next(c for c in result.board.columns if c.id == "todo")
        assert not any(t.id == "task-1" for t in todo.tasks)

    def test_move_task_same_column(self, board_with_tasks: Board):
        """Test reordering a task within the same column."""
        result = move_task(board_with_tasks, "task-1", "todo", "todo", 1)
        assert result.success is True
        # task-1 should now be at index 1
        todo = next(c for c in result.board.columns if c.id == "todo")
        assert todo.tasks[1].id == "task-1"

    def test_move_task_source_not_found(self, board_with_tasks: Board):
        """Test moving from non-existent column."""
        result = move_task(board_with_tasks, "task-1", "nonexistent", "done", 0)
        assert result.success is False
        assert "not found" in result.error

    def test_move_task_target_not_found(self, board_with_tasks: Board):
        """Test moving to non-existent column."""
        result = move_task(board_with_tasks, "task-1", "todo", "nonexistent", 0)
        assert result.success is False
        assert "not found" in result.error

    def test_move_task_not_found(self, board_with_tasks: Board):
        """Test moving non-existent task."""
        result = move_task(board_with_tasks, "task-999", "todo", "done", 0)
        assert result.success is False


class TestAddTask:
    """Tests for add_task."""

    def test_add_task_minimal(self, minimal_board: Board):
        """Test adding a task with minimal input."""
        input_data = TaskInput(title="New Task")
        result = add_task(minimal_board, "todo", input_data)
        assert result.success is True
        assert result.board is not None
        todo = next(c for c in result.board.columns if c.id == "todo")
        assert len(todo.tasks) == 1
        assert todo.tasks[0].title == "New Task"
        assert todo.tasks[0].id == "task-1"

    def test_add_task_full(self, minimal_board: Board):
        """Test adding a task with all fields."""
        input_data = TaskInput(
            title="Full Task",
            description="Description",
            priority=Priority.HIGH,
            tags=["urgent"],
            assignee="alice",
            due_date="2024-12-31",
            related_files=["file.py"],
            subtasks=["Subtask 1", "Subtask 2"],
        )
        result = add_task(minimal_board, "todo", input_data)
        assert result.success is True
        task = result.board.columns[0].tasks[0]
        assert task.priority == Priority.HIGH
        assert task.tags == ["urgent"]
        assert task.subtasks is not None
        assert len(task.subtasks) == 2

    def test_add_task_empty_title(self, minimal_board: Board):
        """Test adding a task with empty title fails."""
        input_data = TaskInput(title="")
        result = add_task(minimal_board, "todo", input_data)
        assert result.success is False
        assert "title" in result.error.lower()

    def test_add_task_column_not_found(self, minimal_board: Board):
        """Test adding to non-existent column."""
        input_data = TaskInput(title="New Task")
        result = add_task(minimal_board, "nonexistent", input_data)
        assert result.success is False


class TestUpdateTask:
    """Tests for update_task."""

    def test_update_task(self, board_with_tasks: Board):
        """Test updating a task."""
        result = update_task(
            board_with_tasks, "todo", "task-1", "Updated Title", "Updated Description"
        )
        assert result.success is True
        todo = next(c for c in result.board.columns if c.id == "todo")
        task = next(t for t in todo.tasks if t.id == "task-1")
        assert task.title == "Updated Title"
        assert task.description == "Updated Description"

    def test_update_task_not_found(self, board_with_tasks: Board):
        """Test updating non-existent task."""
        result = update_task(board_with_tasks, "todo", "task-999", "Title", "Desc")
        assert result.success is False


class TestDeleteTask:
    """Tests for delete_task."""

    def test_delete_task(self, board_with_tasks: Board):
        """Test deleting a task."""
        result = delete_task(board_with_tasks, "todo", "task-1")
        assert result.success is True
        todo = next(c for c in result.board.columns if c.id == "todo")
        assert not any(t.id == "task-1" for t in todo.tasks)

    def test_delete_task_not_found(self, board_with_tasks: Board):
        """Test deleting non-existent task."""
        result = delete_task(board_with_tasks, "todo", "task-999")
        assert result.success is False


class TestPatchTask:
    """Tests for patch_task."""

    def test_patch_task_title(self, board_with_tasks: Board):
        """Test patching task title."""
        patch = TaskPatch(title="Patched Title")
        result = patch_task(board_with_tasks, "task-1", patch)
        assert result.success is True
        task = next(
            t for c in result.board.columns for t in c.tasks if t.id == "task-1"
        )
        assert task.title == "Patched Title"

    def test_patch_task_remove_field(self, board_with_tasks: Board):
        """Test removing a field with None."""
        patch = TaskPatch(description=None)
        result = patch_task(board_with_tasks, "task-1", patch)
        assert result.success is True
        task = next(
            t for c in result.board.columns for t in c.tasks if t.id == "task-1"
        )
        assert task.description is None

    def test_patch_task_not_found(self, board_with_tasks: Board):
        """Test patching non-existent task."""
        patch = TaskPatch(title="New Title")
        result = patch_task(board_with_tasks, "task-999", patch)
        assert result.success is False


class TestArchiveTask:
    """Tests for archive_task."""

    def test_archive_task(self, board_with_tasks: Board):
        """Test archiving a task."""
        result = archive_task(board_with_tasks, "todo", "task-1")
        assert result.success is True
        # Task should not be in column
        todo = next(c for c in result.board.columns if c.id == "todo")
        assert not any(t.id == "task-1" for t in todo.tasks)
        # Task should be in archive
        assert result.board.archive is not None
        assert any(t.id == "task-1" for t in result.board.archive)

    def test_archive_task_not_found(self, board_with_tasks: Board):
        """Test archiving non-existent task."""
        result = archive_task(board_with_tasks, "todo", "task-999")
        assert result.success is False


class TestRestoreTask:
    """Tests for restore_task."""

    def test_restore_task(self, complex_board: Board):
        """Test restoring a task from archive."""
        result = restore_task(complex_board, "archived-1", "todo")
        assert result.success is True
        # Task should be in column
        todo = next(c for c in result.board.columns if c.id == "todo")
        assert any(t.id == "archived-1" for t in todo.tasks)
        # Task should not be in archive
        assert not any(t.id == "archived-1" for t in result.board.archive)

    def test_restore_task_empty_archive(self, minimal_board: Board):
        """Test restoring from empty archive."""
        result = restore_task(minimal_board, "task-1", "todo")
        assert result.success is False
        assert "empty" in result.error.lower()


class TestSubtaskOperations:
    """Tests for subtask operations."""

    def test_toggle_subtask(self, board_with_subtasks: Board):
        """Test toggling a subtask."""
        result = toggle_subtask(board_with_subtasks, "task-1", "task-1-1")
        assert result.success is True
        task = result.board.columns[0].tasks[0]
        subtask = next(s for s in task.subtasks if s.id == "task-1-1")
        assert subtask.completed is True  # Was False

    def test_add_subtask(self, board_with_tasks: Board):
        """Test adding a subtask."""
        result = add_subtask(board_with_tasks, "task-1", "New Subtask")
        assert result.success is True
        task = next(
            t for c in result.board.columns for t in c.tasks if t.id == "task-1"
        )
        assert task.subtasks is not None
        assert len(task.subtasks) == 1
        assert task.subtasks[0].title == "New Subtask"

    def test_delete_subtask(self, board_with_subtasks: Board):
        """Test deleting a subtask."""
        result = delete_subtask(board_with_subtasks, "task-1", "task-1-1")
        assert result.success is True
        task = result.board.columns[0].tasks[0]
        assert not any(s.id == "task-1-1" for s in task.subtasks)

    def test_update_subtask(self, board_with_subtasks: Board):
        """Test updating a subtask title."""
        result = update_subtask(board_with_subtasks, "task-1", "task-1-1", "Updated")
        assert result.success is True
        task = result.board.columns[0].tasks[0]
        subtask = next(s for s in task.subtasks if s.id == "task-1-1")
        assert subtask.title == "Updated"

    def test_set_subtasks_completed(self, board_with_subtasks: Board):
        """Test setting multiple subtasks completed."""
        result = set_subtasks_completed(
            board_with_subtasks, "task-1", ["task-1-1", "task-1-3"], True
        )
        assert result.success is True
        task = result.board.columns[0].tasks[0]
        assert next(s for s in task.subtasks if s.id == "task-1-1").completed is True
        assert next(s for s in task.subtasks if s.id == "task-1-3").completed is True

    def test_set_all_subtasks_completed(self, board_with_subtasks: Board):
        """Test setting all subtasks completed."""
        result = set_all_subtasks_completed(board_with_subtasks, "task-1", True)
        assert result.success is True
        task = result.board.columns[0].tasks[0]
        assert all(s.completed for s in task.subtasks)


class TestBulkOperations:
    """Tests for bulk operations."""

    def test_move_tasks(self, board_with_tasks: Board):
        """Test moving multiple tasks."""
        result = move_tasks(board_with_tasks, ["task-1", "task-2"], "done")
        assert result.success is True
        assert result.success_count == 2
        done = next(c for c in result.board.columns if c.id == "done")
        assert len(done.tasks) == 2

    def test_patch_tasks(self, board_with_tasks: Board):
        """Test patching multiple tasks."""
        patch = TaskPatch(priority=Priority.LOW)
        result = patch_tasks(board_with_tasks, ["task-1", "task-2"], patch)
        assert result.success is True
        assert result.success_count == 2

    def test_delete_tasks(self, board_with_tasks: Board):
        """Test deleting multiple tasks."""
        result = delete_tasks(board_with_tasks, ["task-1", "task-2"])
        assert result.success is True
        assert result.success_count == 2

    def test_archive_tasks(self, board_with_tasks: Board):
        """Test archiving multiple tasks."""
        result = archive_tasks(board_with_tasks, ["task-1", "task-2"])
        assert result.success is True
        assert result.success_count == 2
        assert len(result.board.archive) == 2

    def test_bulk_partial_failure(self, board_with_tasks: Board):
        """Test bulk operation with partial failure."""
        result = move_tasks(
            board_with_tasks, ["task-1", "task-999"], "done"
        )  # task-999 doesn't exist
        assert result.success is False
        assert result.success_count == 1
        assert result.failure_count == 1


class TestUpdateBoardTitle:
    """Tests for update_board_title."""

    def test_update_title(self, minimal_board: Board):
        """Test updating board title."""
        result = update_board_title(minimal_board, "New Title")
        assert result.success is True
        assert result.board.title == "New Title"


class TestUpdateStatsConfig:
    """Tests for update_stats_config."""

    def test_update_stats_config(self, minimal_board: Board):
        """Test updating stats config."""
        result = update_stats_config(minimal_board, ["todo", "done"])
        assert result.success is True
        assert result.board.stats_config is not None
        assert result.board.stats_config.columns == ["todo", "done"]
