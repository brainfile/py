"""
Data models for the Brainfile protocol.

Core data structures: BoardConfig, Task, TaskDocument, Contract, and related types.

These are plain dataclasses (no Pydantic dependency). Each model supports:
- Construction via keyword arguments (snake_case)
- Construction via ``Model.model_validate(dict)`` for camelCase or snake_case dicts
- Serialization via ``model.model_dump(by_alias=True, exclude_none=True)``
- Shallow copy via ``model.model_copy(update={...})``
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any, Literal

from ._keys import camel_to_snake, keys_to_camel


# =============================================================================
# Helpers
# =============================================================================


def _strip_none(d: dict[str, Any]) -> dict[str, Any]:
    """Remove keys whose value is None."""
    return {k: v for k, v in d.items() if v is not None}


class _ModelMixin:
    """Mixin providing Pydantic-compatible class methods on plain dataclasses.

    Unknown keys passed to ``model_validate()`` are preserved in ``_extras``
    and merged back during ``model_dump()``.  This enables round-tripping of
    extension fields (e.g. ``x-otto``, ``x-cursor``) without data loss.
    """

    def __post_init__(self) -> None:
        if not hasattr(self, "_extras"):
            object.__setattr__(self, "_extras", {})

    @classmethod
    def model_validate(cls, data: dict[str, Any] | Any) -> Any:
        """Construct an instance from a dict (camelCase or snake_case keys)."""
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        resolved, extras = _resolve_fields(cls, data)
        instance = cls(**resolved)
        object.__setattr__(instance, "_extras", extras)
        return instance

    def model_dump(
        self,
        by_alias: bool = False,
        exclude_none: bool = False,
        mode: str | None = None,
    ) -> dict[str, Any]:
        """Serialize to a plain dict, including preserved extension fields."""
        result = _dataclass_to_dict(self)
        # Merge extras back (extension fields like x-otto) — values are opaque,
        # only top-level keys are transformed (x- keys pass through unchanged)
        extras = getattr(self, "_extras", {})
        if by_alias:
            result = keys_to_camel(result)
        # Inject extras after key transform — values are opaque (not transformed)
        if extras:
            result.update(extras)
        if exclude_none:
            result = _deep_strip_none(result)
        return result

    def model_copy(self, update: dict[str, Any] | None = None) -> Any:
        """Return a shallow copy with optional field overrides."""
        data = _dataclass_to_dict(self)
        if update:
            data.update(update)
        copy = self.__class__(**data)
        object.__setattr__(copy, "_extras", dict(getattr(self, "_extras", {})))
        return copy


def _dataclass_to_dict(obj: Any) -> dict[str, Any]:
    """Convert a dataclass to a dict, recursing into nested dataclasses and lists."""
    if not hasattr(obj, "__dataclass_fields__"):
        return obj
    result: dict[str, Any] = {}
    for f in fields(obj):
        if f.name == "_extras":
            continue  # merged separately by model_dump()
        value = getattr(obj, f.name)
        result[f.name] = _serialize_value(value)
    return result


def _serialize_value(value: Any) -> Any:
    """Serialize a value for dict output."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    return value


def _deep_strip_none(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively remove None-valued keys."""
    result: dict[str, Any] = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, dict):
            result[k] = _deep_strip_none(v)
        elif isinstance(v, list):
            result[k] = [
                _deep_strip_none(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            result[k] = v
    return result


def _resolve_fields(cls: type, data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Map a dict (with camelCase or snake_case keys) to dataclass constructor kwargs.

    Returns ``(kwargs, extras)`` where extras contains unknown keys preserved
    for round-tripping (e.g. ``x-otto``, ``x-cursor`` extension fields).
    """
    # Build a lookup of all field names
    field_names = {f.name for f in fields(cls)}
    kwargs: dict[str, Any] = {}
    extras: dict[str, Any] = {}

    for key, value in data.items():
        # Try the key as-is first (snake_case)
        if key in field_names:
            kwargs[key] = _coerce_field(cls, key, value)
            continue
        # Try converting from camelCase
        snake_key = camel_to_snake(key)
        if snake_key in field_names:
            kwargs[snake_key] = _coerce_field(cls, snake_key, value)
            continue
        # Preserve unknown keys in extras for round-tripping
        extras[key] = value

    return kwargs, extras


def _coerce_nested_model_value(target_cls_name: str | None, value: Any) -> Any:
    if target_cls_name is None:
        return value

    target_cls = globals()[target_cls_name]
    if isinstance(value, list):
        return [
            target_cls.model_validate(item) if isinstance(item, dict) else item
            for item in value
        ]
    if isinstance(value, dict):
        return target_cls.model_validate(value)
    return value


def _coerce_types_config(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    return {
        k: TypeEntry.model_validate(v) if isinstance(v, dict) else v
        for k, v in value.items()
    }


def _coerce_field(cls: type, field_name: str, value: Any) -> Any:
    """Coerce a value to the expected type for a field."""
    cls_name = cls.__name__
    model_map = NESTED_MODELS.get(cls_name, {})
    nested_model = model_map.get(field_name)

    if field_name in model_map:
        return _coerce_nested_model_value(nested_model, value)

    if cls_name == "BoardConfig" and field_name == "types":
        return _coerce_types_config(value)

    return value


# =============================================================================
# Enums
# =============================================================================


class BrainfileType(str, Enum):
    """
    Brainfile type names.

    The type system is OPEN -- any string value is valid.
    These are reference examples from official schemas.
    """

    BOARD = "board"
    JOURNAL = "journal"
    COLLECTION = "collection"
    CHECKLIST = "checklist"
    DOCUMENT = "document"


class RendererType(str, Enum):
    """Renderer types for displaying brainfiles."""

    KANBAN = "kanban"
    TIMELINE = "timeline"
    CHECKLIST = "checklist"
    GROUPED_LIST = "grouped-list"
    DOCUMENT = "document"
    TREE = "tree"


class Priority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TemplateType(str, Enum):
    """Built-in template types."""

    BUG = "bug"
    FEATURE = "feature"
    REFACTOR = "refactor"


# =============================================================================
# Base Types
# =============================================================================


@dataclass
class Rule(_ModelMixin):
    """Rule definition for project guidelines."""

    id: int = 0
    rule: str = ""


@dataclass
class Rules(_ModelMixin):
    """Rules structure with different priority levels."""

    always: list[Rule] | None = None
    never: list[Rule] | None = None
    prefer: list[Rule] | None = None
    context: list[Rule] | None = None


@dataclass
class AgentInstructions(_ModelMixin):
    """AI agent instructions."""

    instructions: list[str] = field(default_factory=list)
    llm_notes: str | None = None
    identity: str | None = None


@dataclass
class StatsConfig(_ModelMixin):
    """Statistics configuration."""

    columns: list[str] | None = None


@dataclass
class Subtask(_ModelMixin):
    """Subtask definition used by tasks."""

    id: str = ""
    title: str = ""
    completed: bool = False


# =============================================================================
# Contract System Types
# =============================================================================


@dataclass
class Deliverable(_ModelMixin):
    """Represents a single deliverable in a contract."""

    type: str = ""
    path: str = ""
    description: str | None = None


@dataclass
class ValidationConfig(_ModelMixin):
    """Commands and configuration for validating contract deliverables."""

    commands: list[str] | None = None


@dataclass
class ContractContext(_ModelMixin):
    """Contextual information for understanding task requirements."""

    background: str | None = None
    relevant_files: list[str] | None = None
    out_of_scope: list[str] | None = None


@dataclass
class ContractMetrics(_ModelMixin):
    """Metrics for tracking contract lifecycle and performance."""

    picked_up_at: str | None = None
    delivered_at: str | None = None
    duration: int | None = None
    rework_count: int | None = None


ContractStatus = Literal["draft", "ready", "in_progress", "delivered", "done", "failed"]
"""Contract status type."""


@dataclass
class Contract(_ModelMixin):
    """Complete contract specification for agent task execution."""

    status: ContractStatus = "draft"
    deliverables: list[Deliverable] | None = None
    validation: ValidationConfig | None = None
    constraints: list[str] | None = None
    context: ContractContext | None = None
    metrics: ContractMetrics | None = None


@dataclass
class ContractPatch(_ModelMixin):
    """Partial update to a contract."""

    status: ContractStatus | None = None
    deliverables: list[Deliverable] | None = None
    validation: ValidationConfig | None = None
    constraints: list[str] | None = None
    context: ContractContext | None = None
    metrics: ContractMetrics | None = None


# =============================================================================
# Task
# =============================================================================


@dataclass
class Task(_ModelMixin):
    """Task definition -- the core unit of work in brainfile."""

    id: str = ""
    title: str = ""
    parent_id: str | None = None
    description: str | None = None
    related_files: list[str] | None = None
    assignee: str | None = None
    tags: list[str] | None = None
    priority: Any = None  # Priority enum or str
    due_date: str | None = None
    subtasks: list[Subtask] | None = None
    template: Any = None  # TemplateType enum or str
    created_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None
    column: str | None = None
    position: int | None = None
    contract: Contract | None = None
    type: str | None = None


@dataclass
class TemplateVariable(_ModelMixin):
    """Variable definition for task templates."""

    name: str = ""
    description: str = ""
    default_value: str | None = None
    required: bool | None = None


@dataclass
class TaskTemplate(_ModelMixin):
    """Task template definition."""

    id: str = ""
    name: str = ""
    description: str = ""
    template: Task = field(default_factory=Task)
    variables: list[TemplateVariable] | None = None
    is_built_in: bool | None = None


@dataclass
class TemplateConfig(_ModelMixin):
    """Template configuration."""

    built_in_templates: list[TaskTemplate] = field(default_factory=list)
    user_templates: list[TaskTemplate] = field(default_factory=list)


# =============================================================================
# Task File Types
# =============================================================================


@dataclass
class TaskDocument(_ModelMixin):
    """
    Container for a task file (board/*.md or logs/*.md).

    Represents the parsed structure of a single task file:
    - Frontmatter (YAML): Task metadata
    - Body (Markdown): Description + logs
    """

    task: Task = field(default_factory=Task)
    body: str = ""
    file_path: str | None = None


# =============================================================================
# Board Configuration Types
# =============================================================================


@dataclass
class ColumnConfig(_ModelMixin):
    """Configuration for a single board column. Columns don't embed tasks."""

    id: str = ""
    title: str = ""
    order: int | None = None
    completion_column: bool | None = False


@dataclass
class TypeEntry(_ModelMixin):
    """Configuration for a custom task type in strict mode."""

    id_prefix: str = ""
    completable: bool | None = True
    schema_url: str | None = None


TypesConfig = dict[str, TypeEntry]
"""Type configuration mapping."""


@dataclass
class BoardConfig(_ModelMixin):
    """
    Board configuration (from .brainfile/brainfile.md).

    Distributed board:
    - Config file: .brainfile/brainfile.md (columns, rules, agent, types)
    - Active tasks: .brainfile/board/*.md (individual files)
    - Archived tasks: .brainfile/logs/*.md (individual files)
    """

    title: str | None = None
    type: str = "board"
    columns: list[ColumnConfig] = field(default_factory=list)
    strict: bool | None = False
    types: TypesConfig | None = None
    stats_config: dict | None = None
    agent: AgentInstructions | None = None
    rules: Rules | None = None
    metadata: dict | None = None


NESTED_MODELS: dict[str, dict[str, str | None]] = {
    "Task": {
        "subtasks": "Subtask",
        "contract": "Contract",
    },
    "Contract": {
        "deliverables": "Deliverable",
        "validation": "ValidationConfig",
        "context": "ContractContext",
        "metrics": "ContractMetrics",
    },
    "ContractPatch": {
        "deliverables": "Deliverable",
        "validation": "ValidationConfig",
        "context": "ContractContext",
        "metrics": "ContractMetrics",
    },
    "BoardConfig": {
        "columns": "ColumnConfig",
        "agent": "AgentInstructions",
        "rules": "Rules",
    },
    "Rules": {
        "always": "Rule",
        "never": "Rule",
        "prefer": "Rule",
        "context": "Rule",
    },
    "TaskDocument": {
        "task": "Task",
    },
    "TaskTemplate": {
        "template": "Task",
        "variables": "TemplateVariable",
    },
    "TemplateConfig": {
        "built_in_templates": "TaskTemplate",
        "user_templates": "TaskTemplate",
    },
    "TaskContextEntry": {
        "record": None,  # handled via LedgerRecord in types_ledger
    },
}


# =============================================================================
# Type Aliases
# =============================================================================

PriorityLiteral = Literal["low", "medium", "high", "critical"]
TemplateLiteral = Literal["bug", "feature", "refactor"]
RuleTypeLiteral = Literal["always", "never", "prefer", "context"]
