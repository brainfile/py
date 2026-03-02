"""Tests for dataclass models."""

import pytest

from brainfile import (
    BRAINFILE_BASENAME,
    BRAINFILE_STATE_BASENAME,
    BoardConfig,
    BrainfileResolutionKind,
    ColumnConfig,
    ContractPatch,
    DOT_BRAINFILE_DIRNAME,
    DOT_BRAINFILE_GITIGNORE_BASENAME,
    Priority,
    Subtask,
    Task,
    TaskDocument,
    TemplateType,
)
from brainfile.task_file import parse_task_content, serialize_task_content


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


class TestBoardConfig:
    """Tests for the BoardConfig model."""

    def test_minimal_config(self):
        """Test creating a minimal board config."""
        config = BoardConfig(
            columns=[ColumnConfig(id="todo", title="To Do")]
        )
        assert len(config.columns) == 1
        assert config.columns[0].id == "todo"

    def test_config_from_dict(self):
        """Test creating board config from dict."""
        data = {
            "title": "Test Board",
            "columns": [
                {"id": "todo", "title": "To Do"},
                {"id": "done", "title": "Done", "completionColumn": True},
            ],
        }
        config = BoardConfig.model_validate(data)
        assert config.title == "Test Board"
        assert len(config.columns) == 2
        assert config.columns[1].completion_column is True


class TestColumnConfig:
    """Tests for the ColumnConfig model."""

    def test_minimal_column(self):
        """Test creating a column with required fields."""
        col = ColumnConfig(id="todo", title="To Do")
        assert col.id == "todo"
        assert col.title == "To Do"
        assert col.completion_column is False

    def test_completion_column(self):
        """Test creating a completion column."""
        col = ColumnConfig(id="done", title="Done", completion_column=True)
        assert col.completion_column is True


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
        assert ContractPatch.__module__ == "brainfile.models"
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


class TestExtensionFields:
    """Extension fields (x-* prefix) survive round-trips through parse/serialize."""

    def test_model_validate_preserves_unknown_keys(self):
        t = Task.model_validate({
            "id": "task-1",
            "title": "Test",
            "x-otto": {"model_chain": ["gpt-4", "claude"], "status": "running"},
            "x-cursor": {"tab_id": 42},
        })
        assert t._extras == {
            "x-otto": {"model_chain": ["gpt-4", "claude"], "status": "running"},
            "x-cursor": {"tab_id": 42},
        }

    def test_model_dump_includes_extras(self):
        t = Task.model_validate({
            "id": "task-1",
            "title": "Test",
            "x-otto": {"status": "done"},
        })
        d = t.model_dump(by_alias=True, exclude_none=True)
        assert d["x-otto"] == {"status": "done"}
        assert "id" in d

    def test_extension_values_are_opaque(self):
        """brainfile must NOT transform keys inside extension values."""
        t = Task.model_validate({
            "id": "task-1",
            "title": "Test",
            "x-otto": {"model_chain": ["a"], "retry_count": 3},
        })
        d = t.model_dump(by_alias=True, exclude_none=True)
        # Keys inside x-otto must stay as-is (snake_case), not be camel-cased
        assert "model_chain" in d["x-otto"]
        assert "retry_count" in d["x-otto"]

    def test_model_copy_preserves_extras(self):
        t = Task.model_validate({
            "id": "task-1",
            "title": "Test",
            "x-otto": {"status": "running"},
        })
        copy = t.model_copy(update={"title": "Updated"})
        assert copy.title == "Updated"
        assert copy._extras == {"x-otto": {"status": "running"}}

    def test_yaml_round_trip(self):
        """x-* fields survive parse → serialize → parse cycle."""
        t = Task.model_validate({
            "id": "task-1",
            "title": "Test",
            "x-otto": {"model_chain": ["gpt-4"], "status": "running"},
        })
        yaml_out = serialize_task_content(t, "## Description\nHello\n")
        assert "x-otto:" in yaml_out

        doc = parse_task_content(yaml_out)
        assert doc.task._extras["x-otto"] == {"model_chain": ["gpt-4"], "status": "running"}

    def test_non_extension_unknown_keys_also_preserved(self):
        """Any unknown key is preserved, not just x-* prefixed ones."""
        t = Task.model_validate({
            "id": "task-1",
            "title": "Test",
            "customField": "hello",
        })
        assert t._extras == {"customField": "hello"}
        d = t.model_dump(by_alias=True, exclude_none=True)
        assert d["customField"] == "hello"
