"""Tests for the realtime module."""

import pytest

from brainfile import (
    Board,
    BoardDiff,
    Column,
    ColumnDiff,
    Task,
    TaskDiff,
    diff_boards,
    hash_board,
    hash_board_content,
)


class TestHashBoardContent:
    """Tests for hash_board_content."""

    def test_hash_same_content(self):
        """Test that same content produces same hash."""
        content = "---\ntitle: Test\ncolumns: []\n---\n"
        hash1 = hash_board_content(content)
        hash2 = hash_board_content(content)
        assert hash1 == hash2

    def test_hash_different_content(self):
        """Test that different content produces different hash."""
        content1 = "---\ntitle: Test 1\ncolumns: []\n---\n"
        content2 = "---\ntitle: Test 2\ncolumns: []\n---\n"
        hash1 = hash_board_content(content1)
        hash2 = hash_board_content(content2)
        assert hash1 != hash2

    def test_hash_is_sha256(self):
        """Test that hash is SHA-256 (64 hex chars)."""
        content = "test"
        hash_result = hash_board_content(content)
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)


class TestHashBoard:
    """Tests for hash_board."""

    def test_hash_board(self, minimal_board: Board):
        """Test hashing a board object."""
        hash_result = hash_board(minimal_board)
        assert len(hash_result) == 64

    def test_hash_same_board_twice(self, minimal_board: Board):
        """Test that same board produces same hash."""
        hash1 = hash_board(minimal_board)
        hash2 = hash_board(minimal_board)
        assert hash1 == hash2

    def test_hash_different_boards(self, minimal_board: Board, complex_board: Board):
        """Test that different boards produce different hashes."""
        hash1 = hash_board(minimal_board)
        hash2 = hash_board(complex_board)
        assert hash1 != hash2


class TestDiffBoards:
    """Tests for diff_boards."""

    def test_identical_boards(self, minimal_board: Board):
        """Test diffing identical boards."""
        diff = diff_boards(minimal_board, minimal_board)
        assert diff.metadata_changed is False
        assert len(diff.columns_added) == 0
        assert len(diff.columns_removed) == 0
        assert len(diff.tasks_added) == 0
        assert len(diff.tasks_removed) == 0

    def test_metadata_changed(self):
        """Test detecting metadata changes."""
        board1 = Board(title="Before", columns=[])
        board2 = Board(title="After", columns=[])
        diff = diff_boards(board1, board2)
        assert diff.metadata_changed is True

    def test_column_added(self):
        """Test detecting added column."""
        board1 = Board(title="Test", columns=[])
        board2 = Board(
            title="Test",
            columns=[Column(id="todo", title="To Do", tasks=[])],
        )
        diff = diff_boards(board1, board2)
        assert len(diff.columns_added) == 1
        assert diff.columns_added[0].column_id == "todo"

    def test_column_removed(self):
        """Test detecting removed column."""
        board1 = Board(
            title="Test",
            columns=[Column(id="todo", title="To Do", tasks=[])],
        )
        board2 = Board(title="Test", columns=[])
        diff = diff_boards(board1, board2)
        assert len(diff.columns_removed) == 1
        assert diff.columns_removed[0].column_id == "todo"

    def test_column_updated(self):
        """Test detecting updated column."""
        board1 = Board(
            title="Test",
            columns=[Column(id="todo", title="To Do", tasks=[])],
        )
        board2 = Board(
            title="Test",
            columns=[Column(id="todo", title="Updated Title", tasks=[])],
        )
        diff = diff_boards(board1, board2)
        assert len(diff.columns_updated) == 1
        assert diff.columns_updated[0].column_id == "todo"
        assert "title" in diff.columns_updated[0].changed_fields

    def test_column_moved(self):
        """Test detecting moved column."""
        board1 = Board(
            title="Test",
            columns=[
                Column(id="todo", title="To Do", tasks=[]),
                Column(id="done", title="Done", tasks=[]),
            ],
        )
        board2 = Board(
            title="Test",
            columns=[
                Column(id="done", title="Done", tasks=[]),
                Column(id="todo", title="To Do", tasks=[]),
            ],
        )
        diff = diff_boards(board1, board2)
        assert len(diff.columns_moved) == 2  # Both columns changed position

    def test_task_added(self):
        """Test detecting added task."""
        board1 = Board(
            title="Test",
            columns=[Column(id="todo", title="To Do", tasks=[])],
        )
        board2 = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[Task(id="task-1", title="New Task")],
                )
            ],
        )
        diff = diff_boards(board1, board2)
        assert len(diff.tasks_added) == 1
        assert diff.tasks_added[0].task_id == "task-1"
        assert diff.tasks_added[0].to_column_id == "todo"

    def test_task_removed(self):
        """Test detecting removed task."""
        board1 = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[Task(id="task-1", title="Task")],
                )
            ],
        )
        board2 = Board(
            title="Test",
            columns=[Column(id="todo", title="To Do", tasks=[])],
        )
        diff = diff_boards(board1, board2)
        assert len(diff.tasks_removed) == 1
        assert diff.tasks_removed[0].task_id == "task-1"
        assert diff.tasks_removed[0].from_column_id == "todo"

    def test_task_updated(self):
        """Test detecting updated task."""
        board1 = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[Task(id="task-1", title="Before")],
                )
            ],
        )
        board2 = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[Task(id="task-1", title="After")],
                )
            ],
        )
        diff = diff_boards(board1, board2)
        assert len(diff.tasks_updated) == 1
        assert diff.tasks_updated[0].task_id == "task-1"
        assert "title" in diff.tasks_updated[0].changed_fields

    def test_task_moved_between_columns(self):
        """Test detecting task moved between columns."""
        board1 = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[Task(id="task-1", title="Task")],
                ),
                Column(id="done", title="Done", tasks=[]),
            ],
        )
        board2 = Board(
            title="Test",
            columns=[
                Column(id="todo", title="To Do", tasks=[]),
                Column(
                    id="done",
                    title="Done",
                    tasks=[Task(id="task-1", title="Task")],
                ),
            ],
        )
        diff = diff_boards(board1, board2)
        assert len(diff.tasks_moved) == 1
        assert diff.tasks_moved[0].task_id == "task-1"
        assert diff.tasks_moved[0].from_column_id == "todo"
        assert diff.tasks_moved[0].to_column_id == "done"

    def test_task_reordered_same_column(self):
        """Test detecting task reordered within same column."""
        board1 = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[
                        Task(id="task-1", title="Task 1"),
                        Task(id="task-2", title="Task 2"),
                    ],
                )
            ],
        )
        board2 = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[
                        Task(id="task-2", title="Task 2"),
                        Task(id="task-1", title="Task 1"),
                    ],
                )
            ],
        )
        diff = diff_boards(board1, board2)
        assert len(diff.tasks_moved) == 2  # Both tasks changed position


class TestColumnDiff:
    """Tests for ColumnDiff dataclass."""

    def test_column_diff_attributes(self):
        """Test ColumnDiff attributes."""
        column = Column(id="todo", title="To Do", tasks=[])
        diff = ColumnDiff(
            column_id="todo",
            before=column,
            after=column,
            from_index=0,
            to_index=1,
            changed_fields=["title"],
        )
        assert diff.column_id == "todo"
        assert diff.before == column
        assert diff.after == column
        assert diff.from_index == 0
        assert diff.to_index == 1
        assert diff.changed_fields == ["title"]


class TestTaskDiff:
    """Tests for TaskDiff dataclass."""

    def test_task_diff_attributes(self):
        """Test TaskDiff attributes."""
        task = Task(id="task-1", title="Task")
        diff = TaskDiff(
            task_id="task-1",
            before=task,
            after=task,
            from_column_id="todo",
            to_column_id="done",
            from_index=0,
            to_index=0,
            changed_fields=["title"],
        )
        assert diff.task_id == "task-1"
        assert diff.before == task
        assert diff.after == task
        assert diff.from_column_id == "todo"
        assert diff.to_column_id == "done"
        assert diff.from_index == 0
        assert diff.to_index == 0
        assert diff.changed_fields == ["title"]


class TestBoardDiff:
    """Tests for BoardDiff dataclass."""

    def test_board_diff_defaults(self):
        """Test BoardDiff default values."""
        diff = BoardDiff()
        assert diff.metadata_changed is False
        assert diff.columns_added == []
        assert diff.columns_removed == []
        assert diff.columns_updated == []
        assert diff.columns_moved == []
        assert diff.tasks_added == []
        assert diff.tasks_removed == []
        assert diff.tasks_updated == []
        assert diff.tasks_moved == []

    def test_board_diff_with_values(self):
        """Test BoardDiff with custom values."""
        task_diff = TaskDiff(task_id="task-1")
        column_diff = ColumnDiff(column_id="todo")
        diff = BoardDiff(
            metadata_changed=True,
            columns_added=[column_diff],
            tasks_added=[task_diff],
        )
        assert diff.metadata_changed is True
        assert len(diff.columns_added) == 1
        assert len(diff.tasks_added) == 1


class TestComplexDiffScenarios:
    """Tests for complex diff scenarios."""

    def test_multiple_changes_at_once(self):
        """Test detecting multiple types of changes simultaneously."""
        board1 = Board(
            title="Before",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[
                        Task(id="task-1", title="Task 1"),
                        Task(id="task-2", title="Task 2"),
                    ],
                ),
                Column(id="done", title="Done", tasks=[]),
            ],
        )
        board2 = Board(
            title="After",  # Metadata changed
            columns=[
                Column(
                    id="todo",
                    title="To Do Updated",  # Column updated
                    tasks=[
                        Task(id="task-1", title="Task 1 Updated"),  # Task updated
                        Task(id="task-3", title="Task 3"),  # Task added
                    ],
                ),
                # task-2 removed, done column moved
                Column(id="done", title="Done", tasks=[]),
            ],
        )
        diff = diff_boards(board1, board2)

        assert diff.metadata_changed is True
        assert len(diff.columns_updated) == 1  # todo updated
        assert len(diff.tasks_removed) == 1  # task-2 removed
        assert len(diff.tasks_added) == 1  # task-3 added
        assert len(diff.tasks_updated) >= 1  # task-1 updated

    def test_task_description_change(self):
        """Test detecting task description changes."""
        board1 = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[Task(id="task-1", title="Task", description="Before")],
                )
            ],
        )
        board2 = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[Task(id="task-1", title="Task", description="After")],
                )
            ],
        )
        diff = diff_boards(board1, board2)
        assert len(diff.tasks_updated) == 1
        assert "description" in diff.tasks_updated[0].changed_fields

    def test_task_priority_change(self):
        """Test detecting task priority changes."""
        from brainfile import Priority

        board1 = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[Task(id="task-1", title="Task", priority=Priority.LOW)],
                )
            ],
        )
        board2 = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[Task(id="task-1", title="Task", priority=Priority.HIGH)],
                )
            ],
        )
        diff = diff_boards(board1, board2)
        assert len(diff.tasks_updated) == 1
        assert "priority" in diff.tasks_updated[0].changed_fields

    def test_task_tags_change(self):
        """Test detecting task tags changes."""
        board1 = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[Task(id="task-1", title="Task", tags=["old"])],
                )
            ],
        )
        board2 = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[Task(id="task-1", title="Task", tags=["new"])],
                )
            ],
        )
        diff = diff_boards(board1, board2)
        assert len(diff.tasks_updated) == 1
        assert "tags" in diff.tasks_updated[0].changed_fields
