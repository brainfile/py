"""
Pydantic data models for Brainfile types.

This module defines all the core data structures used in brainfiles,
including Board, Column, Task, Subtask, Journal, and related types.
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
    Example brainfile type names.

    IMPORTANT: The type system is OPEN - any string value is valid.
    These are just reference examples from official schemas.

    Custom types work identically:
    - 'sprint-board' with columns[] -> kanban renderer (same as 'board')
    - 'dev-log' with entries[] -> timeline renderer (same as 'journal')

    Type names are metadata only. Structure determines behavior.
    """

    BOARD = "board"
    JOURNAL = "journal"
    COLLECTION = "collection"
    CHECKLIST = "checklist"
    DOCUMENT = "document"


class RendererType(str, Enum):
    """
    Renderer types for displaying brainfiles.

    Renderers are selected by:
    1. Schema hints (x-brainfile-renderer) - explicit override
    2. Structural patterns - detect from data shape
    3. Fallback to tree view

    No special treatment for official types - everyone uses structural inference.
    """

    KANBAN = "kanban"
    """Kanban board with columns and draggable cards"""

    TIMELINE = "timeline"
    """Timeline/chronological view with timestamps"""

    CHECKLIST = "checklist"
    """Simple flat checklist with completion tracking"""

    GROUPED_LIST = "grouped-list"
    """Grouped list with categories"""

    DOCUMENT = "document"
    """Document viewer for structured content"""

    TREE = "tree"
    """Generic tree view (fallback for unknown types)"""


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
    """Column IDs to display in stats (max 4)"""


class Subtask(BaseModel):
    """Subtask definition used by tasks."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    completed: bool = False


class Task(BaseModel):
    """Task definition - used by board type."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    description: str | None = None
    related_files: list[str] | None = Field(default=None, alias="relatedFiles")
    assignee: str | None = None
    tags: list[str] | None = None
    priority: Priority | None = None
    due_date: str | None = Field(default=None, alias="dueDate")
    subtasks: list[Subtask] | None = None
    template: TemplateType | None = None
    created_at: str | None = Field(default=None, alias="createdAt")
    """ISO 8601 timestamp"""
    updated_at: str | None = Field(default=None, alias="updatedAt")
    """ISO 8601 timestamp"""


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
# Board Types
# =============================================================================


class Column(BaseModel):
    """Column definition for Kanban boards."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    order: int | None = None
    tasks: list[Task] = Field(default_factory=list)


class Board(BaseModel):
    """
    Board type - Kanban-style task board with columns.

    Extends BrainfileBase with board-specific fields.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Base fields (shared by all brainfile types)
    title: str
    """Brainfile title"""

    type: Literal["board"] | None = None
    """Type discriminator"""

    schema_url: str | None = Field(default=None, alias="schema")
    """Schema URL for validation"""

    protocol_version: str | None = Field(default=None, alias="protocolVersion")
    """Protocol version (semver)"""

    agent: AgentInstructions | None = None
    """AI agent instructions"""

    rules: Rules | None = None
    """Project rules and guidelines"""

    # Board-specific fields
    columns: list[Column] = Field(default_factory=list)
    archive: list[Task] | None = None
    stats_config: StatsConfig | None = Field(default=None, alias="statsConfig")


# =============================================================================
# Union Type
# =============================================================================

# Note: Journal and other types are for community extensions only.
# The official brainfile apps only support the board type.
Brainfile = Board
"""Union type for supported brainfile types (board only in official apps)."""


# =============================================================================
# Type Aliases for Literal Types
# =============================================================================

PriorityLiteral = Literal["low", "medium", "high", "critical"]
TemplateLiteral = Literal["bug", "feature", "refactor"]
RuleTypeLiteral = Literal["always", "never", "prefer", "context"]
