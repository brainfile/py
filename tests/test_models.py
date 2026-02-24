"""Tests for Pydantic models."""

import pytest

from brainfile import (
    BRAINFILE_BASENAME,
    BRAINFILE_STATE_BASENAME,
    Board,
    BrainfileResolutionKind,
    Column,
    ContractPatch,
    DOT_BRAINFILE_DIRNAME,
    DOT_BRAINFILE_GITIGNORE_BASENAME,
    Priority,
    Subtask,
    Task,
    TaskDocument,
    TemplateType,
)


class TestTask:
    """Tests for the Task model."""

    def test_minimal_task(self):
        """Test creating a task with only required fields."""
        task = Task(id="task-1", title="Test Task")
        assert task.id == "task-1"
        assert task.title == "Test Task"
        assert task.description is None
        assert task.priority is None
        assert task.tags is None

    def test_full_task(self):
        """Test creating a task with all fields."""
        task = Task(
            id="task-1",
            title="Test Task",
            description="Test description",
            priority=Priority.HIGH,
            tags=["urgent", "bug"],
            assignee="alice",
            due_date="2024-12-31",
            related_files=["src/main.py"],
            template=TemplateType.BUG,
            subtasks=[
                Subtask(id="task-1-1", title="Subtask 1", completed=False),
            ],
        )
        assert task.priority == Priority.HIGH
        assert task.tags == ["urgent", "bug"]
        assert task.assignee == "alice"
        assert len(task.subtasks) == 1

    def test_task_from_dict_with_alias(self):
        """Test creating a task from dict with camelCase aliases."""
        data = {
            "id": "task-1",
            "title": "Test",
            "dueDate": "2024-12-31",
            "relatedFiles": ["file.py"],
        }
        task = Task.model_validate(data)
        assert task.due_date == "2024-12-31"
        assert task.related_files == ["file.py"]

    def test_task_to_dict_with_alias(self):
        """Test serializing task to dict with camelCase aliases."""
        task = Task(
            id="task-1",
            title="Test",
            due_date="2024-12-31",
            related_files=["file.py"],
        )
        data = task.model_dump(by_alias=True, exclude_none=True)
        assert "dueDate" in data
        assert "relatedFiles" in data
        assert data["dueDate"] == "2024-12-31"


class TestSubtask:
    """Tests for the Subtask model."""

    def test_subtask_creation(self):
        """Test creating a subtask."""
        subtask = Subtask(id="task-1-1", title="Test Subtask", completed=False)
        assert subtask.id == "task-1-1"
        assert subtask.title == "Test Subtask"
        assert subtask.completed is False

    def test_subtask_default_completed(self):
        """Test that completed defaults to False."""
        subtask = Subtask(id="task-1-1", title="Test")
        assert subtask.completed is False


class TestColumn:
    """Tests for the Column model."""

    def test_minimal_column(self):
        """Test creating a column with required fields."""
        column = Column(id="todo", title="To Do", tasks=[])
        assert column.id == "todo"
        assert column.title == "To Do"
        assert column.tasks == []

    def test_column_with_tasks(self):
        """Test creating a column with tasks."""
        column = Column(
            id="todo",
            title="To Do",
            tasks=[
                Task(id="task-1", title="Task 1"),
                Task(id="task-2", title="Task 2"),
            ],
        )
        assert len(column.tasks) == 2

    def test_column_default_tasks(self):
        """Test that tasks defaults to empty list."""
        column = Column(id="todo", title="To Do")
        assert column.tasks == []


class TestBoard:
    """Tests for the Board model."""

    def test_minimal_board(self, minimal_board: Board):
        """Test minimal board fixture."""
        assert minimal_board.title == "Test Board"
        assert len(minimal_board.columns) == 1
        assert minimal_board.columns[0].id == "todo"

    def test_complex_board(self, complex_board: Board):
        """Test complex board fixture."""
        assert complex_board.title == "Complex Board"
        assert complex_board.protocol_version == "1.0"
        assert complex_board.agent is not None
        assert complex_board.rules is not None
        assert complex_board.stats_config is not None
        assert len(complex_board.columns) == 2
        assert complex_board.archive is not None
        assert len(complex_board.archive) == 1

    def test_board_from_dict(self, minimal_board_dict: dict):
        """Test creating a board from dict."""
        board = Board.model_validate(minimal_board_dict)
        assert board.title == "Test Board"
        assert len(board.columns) == 1

    def test_board_deep_copy(self, minimal_board: Board):
        """Test deep copying a board."""
        copy = minimal_board.model_copy(deep=True)
        copy.title = "Modified"
        assert minimal_board.title == "Test Board"
        assert copy.title == "Modified"


class TestPriorityEnum:
    """Tests for the Priority enum."""

    def test_priority_values(self):
        """Test priority enum values."""
        assert Priority.LOW.value == "low"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.HIGH.value == "high"
        assert Priority.CRITICAL.value == "critical"

    def test_priority_from_string(self):
        """Test creating priority from string."""
        assert Priority("high") == Priority.HIGH


class TestTemplateTypeEnum:
    """Tests for the TemplateType enum."""

    def test_template_type_values(self):
        """Test template type enum values."""
        assert TemplateType.BUG.value == "bug"
        assert TemplateType.FEATURE.value == "feature"
        assert TemplateType.REFACTOR.value == "refactor"


class TestTopLevelExportSurface:
    """Regression tests for top-level exports."""

    def test_task_document_exported(self):
        doc = TaskDocument(task=Task(id="task-1", title="Task"), body="Body")
        assert doc.task.id == "task-1"
        assert "TaskDocument" in __import__("brainfile").__all__

    def test_contract_patch_type_exported(self):
        assert ContractPatch.__module__ == "brainfile.contract_ops"
        assert "status" in ContractPatch.__annotations__
        assert "ContractPatch" in __import__("brainfile").__all__

    def test_file_constants_exported(self):
        assert DOT_BRAINFILE_DIRNAME == ".brainfile"
        assert BRAINFILE_BASENAME == "brainfile.md"
        assert BRAINFILE_STATE_BASENAME == "state.json"
        assert DOT_BRAINFILE_GITIGNORE_BASENAME == ".gitignore"

        brainfile_module = __import__("brainfile")
        assert "DOT_BRAINFILE_DIRNAME" in brainfile_module.__all__
        assert "BRAINFILE_BASENAME" in brainfile_module.__all__
        assert "BRAINFILE_STATE_BASENAME" in brainfile_module.__all__
        assert "DOT_BRAINFILE_GITIGNORE_BASENAME" in brainfile_module.__all__

    def test_brainfile_resolution_kind_exported(self):
        assert BrainfileResolutionKind is str
        assert "BrainfileResolutionKind" in __import__("brainfile").__all__
