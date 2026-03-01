"""
Pydantic data models for the Brainfile protocol.

Core data structures: BoardConfig, Task, TaskDocument, Contract, and related types.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Enums
# =============================================================================


class BrainfileType(str, Enum):
    """
    Brainfile type names.

    The type system is OPEN — any string value is valid.
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


class Rule(BaseModel):
    """Rule definition for project guidelines."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    rule: str


class Rules(BaseModel):
    """Rules structure with different priority levels."""

    model_config = ConfigDict(populate_by_name=True)

    always: list[Rule] | None = None
    never: list[Rule] | None = None
    prefer: list[Rule] | None = None
    context: list[Rule] | None = None


class AgentInstructions(BaseModel):
    """AI agent instructions."""

    model_config = ConfigDict(populate_by_name=True)

    instructions: list[str]
    llm_notes: str | None = Field(default=None, alias="llmNotes")


class StatsConfig(BaseModel):
    """Statistics configuration."""

    model_config = ConfigDict(populate_by_name=True)

    columns: list[str] | None = None


class Subtask(BaseModel):
    """Subtask definition used by tasks."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    completed: bool = False


# =============================================================================
# Contract System Types
# =============================================================================


class Deliverable(BaseModel):
    """Represents a single deliverable in a contract."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    type: str = Field(
        description="Deliverable type: 'file' | 'test' | 'doc' | 'link' | 'other' | custom"
    )
    path: str = Field(description="Path to deliverable (file path, URL, etc.)")
    description: str | None = Field(
        default=None,
        description="Human-readable description of deliverable"
    )


class ValidationConfig(BaseModel):
    """Commands and configuration for validating contract deliverables."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    commands: list[str] | None = Field(
        default=None,
        description="Shell commands to run for validation (e.g., tests, linting)"
    )


class ContractContext(BaseModel):
    """Contextual information for understanding task requirements."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    background: str | None = Field(
        default=None,
        description="Background information or requirements"
    )
    relevant_files: list[str] | None = Field(
        default=None,
        alias="relevantFiles",
        description="Files relevant to understanding the task"
    )
    out_of_scope: list[str] | None = Field(
        default=None,
        alias="outOfScope",
        description="Items explicitly out of scope"
    )


class ContractMetrics(BaseModel):
    """Metrics for tracking contract lifecycle and performance."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    picked_up_at: str | None = Field(
        default=None,
        alias="pickedUpAt",
        description="ISO 8601 timestamp when agent picked up task"
    )
    delivered_at: str | None = Field(
        default=None,
        alias="deliveredAt",
        description="ISO 8601 timestamp when deliverables submitted"
    )
    duration: int | None = Field(
        default=None,
        description="Duration in milliseconds from pickup to delivery"
    )
    rework_count: int | None = Field(
        default=None,
        alias="reworkCount",
        description="Number of times contract was reworked"
    )


ContractStatus = Literal["draft", "ready", "in_progress", "delivered", "done", "failed"]
"""Contract status type."""


class Contract(BaseModel):
    """Complete contract specification for agent task execution."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    status: ContractStatus = Field(
        default="draft",
        description="Current contract status"
    )
    deliverables: list[Deliverable] | None = Field(
        default=None,
        description="Required deliverables for contract completion"
    )
    validation: ValidationConfig | None = Field(
        default=None,
        description="Validation configuration and commands"
    )
    constraints: list[str] | None = Field(
        default=None,
        description="Constraints or requirements (e.g., performance, security)"
    )
    context: ContractContext | None = Field(
        default=None,
        description="Context and background for understanding requirements"
    )
    metrics: ContractMetrics | None = Field(
        default=None,
        description="Metrics tracking contract lifecycle"
    )


class ContractPatch(BaseModel):
    """Partial update to a contract."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    status: ContractStatus | None = None
    deliverables: list[Deliverable] | None = None
    validation: ValidationConfig | None = None
    constraints: list[str] | None = None
    context: ContractContext | None = None
    metrics: ContractMetrics | None = None


# =============================================================================
# Task
# =============================================================================


class Task(BaseModel):
    """Task definition — the core unit of work in brainfile."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    parent_id: str | None = Field(
        default=None,
        alias="parentId",
        description="Optional parent task/document ID for parent-child linking",
    )
    description: str | None = None
    related_files: list[str] | None = Field(default=None, alias="relatedFiles")
    assignee: str | None = None
    tags: list[str] | None = None
    priority: Priority | None = None
    due_date: str | None = Field(default=None, alias="dueDate")
    subtasks: list[Subtask] | None = None
    template: TemplateType | None = None
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")
    completed_at: str | None = Field(default=None, alias="completedAt")
    column: str | None = Field(default=None, description="Column ID from frontmatter")
    position: int | None = Field(default=None, description="Position within column for ordering")
    contract: Contract | None = Field(default=None, description="Agent contract specification")
    type: str | None = Field(default=None, description="Custom task type (e.g., 'epic', 'adr')")


class TemplateVariable(BaseModel):
    """Variable definition for task templates."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str
    default_value: str | None = Field(default=None, alias="defaultValue")
    required: bool | None = None


class TaskTemplate(BaseModel):
    """Task template definition."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    description: str
    template: Task
    variables: list[TemplateVariable] | None = None
    is_built_in: bool | None = Field(default=None, alias="isBuiltIn")


class TemplateConfig(BaseModel):
    """Template configuration."""

    model_config = ConfigDict(populate_by_name=True)

    built_in_templates: list[TaskTemplate] = Field(alias="builtInTemplates")
    user_templates: list[TaskTemplate] = Field(alias="userTemplates")


# =============================================================================
# Task File Types
# =============================================================================


class TaskDocument(BaseModel):
    """
    Container for a task file (board/*.md or logs/*.md).

    Represents the parsed structure of a single task file:
    - Frontmatter (YAML): Task metadata
    - Body (Markdown): Description + logs
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    task: Task
    body: str = Field(description="Markdown body: description + logs")
    file_path: str | None = Field(
        default=None,
        alias="filePath",
        description="Full path to task file"
    )


# =============================================================================
# Board Configuration Types
# =============================================================================


class ColumnConfig(BaseModel):
    """Configuration for a single board column. Columns don't embed tasks."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str = Field(description="Unique column identifier")
    title: str = Field(description="Human-readable column title")
    order: int | None = Field(default=None, description="Sort order for column display")
    completion_column: bool | None = Field(
        default=False,
        alias="completionColumn",
        description="If true, marks this as a completion/archive column"
    )


class TypeEntry(BaseModel):
    """Configuration for a custom task type in strict mode."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id_prefix: str = Field(
        alias="idPrefix",
        description="ID prefix for this type (e.g., 'epic', 'adr', 'spike')"
    )
    completable: bool | None = Field(
        default=True,
        description="Whether tasks of this type can be marked complete"
    )
    schema_url: str | None = Field(
        default=None,
        alias="schema",
        description="Optional JSON schema URI for type validation"
    )


TypesConfig = dict[str, TypeEntry]
"""Type configuration mapping."""


class BoardConfig(BaseModel):
    """
    Board configuration (from .brainfile/brainfile.md).

    Distributed board:
    - Config file: .brainfile/brainfile.md (columns, rules, agent, types)
    - Active tasks: .brainfile/board/*.md (individual files)
    - Archived tasks: .brainfile/logs/*.md (individual files)
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    title: str | None = Field(default=None, description="Board title")
    type: Literal["board"] = Field(default="board")
    columns: list[ColumnConfig] = Field(
        description="Column definitions (no embedded tasks)"
    )
    strict: bool | None = Field(
        default=False,
        description="Enable strict type and column validation"
    )
    types: TypesConfig | None = Field(
        default=None,
        description="Custom task type definitions (strict mode)"
    )
    stats_config: dict | None = Field(
        default=None,
        alias="statsConfig",
        description="Statistics and aggregation configuration"
    )
    agent: AgentInstructions | None = Field(default=None)
    rules: Rules | None = Field(default=None)
    metadata: dict | None = Field(default=None)


# =============================================================================
# Type Aliases
# =============================================================================

PriorityLiteral = Literal["low", "medium", "high", "critical"]
TemplateLiteral = Literal["bug", "feature", "refactor"]
RuleTypeLiteral = Literal["always", "never", "prefer", "context"]
