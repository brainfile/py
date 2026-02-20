"""
brainfile - Python library for the Brainfile task management protocol.

This library provides parsing, serialization, validation, and template management
for Brainfile markdown files with YAML frontmatter.

Example:
    >>> from brainfile import Brainfile, Board
    >>>
    >>> # Parse a brainfile
    >>> content = open("brainfile.md").read()
    >>> result = Brainfile.parse_with_errors(content)
    >>> if result.board:
    ...     print(f"Found {len(result.board.columns)} columns")
    >>>
    >>> # Serialize back to markdown
    >>> markdown = Brainfile.serialize(result.board)
"""

from __future__ import annotations

__version__ = "0.1.0"

# =============================================================================
# Models
# =============================================================================

from .models import (
    # Enums
    BrainfileType,
    Priority,
    PriorityLiteral,
    RendererType,
    RuleTypeLiteral,
    TemplateLiteral,
    TemplateType,
    # Base models
    AgentInstructions,
    Rule,
    Rules,
    StatsConfig,
    Subtask,
    Task,
    TaskTemplate,
    TemplateConfig,
    TemplateVariable,
    # Board models
    Board,
    Column,
    # Union type (board only in official apps)
    Brainfile as BrainfileUnion,
)

# =============================================================================
# Parser
# =============================================================================

from .parser import BrainfileParser, ParseResult

# =============================================================================
# Inference
# =============================================================================

from .inference import infer_renderer, infer_type

# =============================================================================
# Schema Hints
# =============================================================================

from .schema_hints import SchemaHints, load_schema_hints, parse_schema_hints

# =============================================================================
# Serializer
# =============================================================================

from .serializer import BrainfileSerializer, SerializeOptions

# =============================================================================
# Validator
# =============================================================================

from .validator import BrainfileValidator, ValidationError, ValidationResult

# =============================================================================
# Linter
# =============================================================================

from .linter import BrainfileLinter, LintIssue, LintOptions, LintResult

# =============================================================================
# Realtime
# =============================================================================

from .realtime import BoardDiff, ColumnDiff, TaskDiff, diff_boards, hash_board, hash_board_content

# =============================================================================
# Templates
# =============================================================================

from .templates import (
    BUILT_IN_TEMPLATES,
    generate_subtask_id,
    generate_task_id,
    get_all_template_ids,
    get_template_by_id,
    process_template,
)

# =============================================================================
# Operations
# =============================================================================

from .operations import (
    BoardOperationResult,
    BulkItemResult,
    BulkOperationResult,
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

# =============================================================================
# Query
# =============================================================================

from .query import (
    TaskInfo,
    column_exists,
    find_column_by_id,
    find_column_by_name,
    find_task_by_id,
    get_all_tasks,
    get_column_task_count,
    get_overdue_tasks,
    get_tasks_by_assignee,
    get_tasks_by_priority,
    get_tasks_by_tag,
    get_tasks_with_incomplete_subtasks,
    get_total_task_count,
    search_tasks,
    task_id_exists,
)

# =============================================================================
# ID Generation
# =============================================================================

from .id_gen import (
    extract_task_id_number,
    generate_next_subtask_id,
    generate_next_task_id,
    generate_subtask_id as generate_subtask_id_from_index,
    get_max_task_id_number,
    get_parent_task_id,
    is_valid_subtask_id,
    is_valid_task_id,
)

# =============================================================================
# Discovery
# =============================================================================

from .discovery import (
    BRAINFILE_GLOBS,
    BRAINFILE_PATTERNS,
    EXCLUDE_DIRS,
    DiscoveredFile,
    DiscoveryOptions,
    DiscoveryResult,
    discover,
    extract_brainfile_suffix,
    find_nearest_brainfile,
    find_primary_brainfile,
    is_brainfile_name,
    watch_brainfiles,
)


# =============================================================================
# Main Facade Class
# =============================================================================


class Brainfile:
    """
    Main Brainfile class providing a high-level API.

    This class provides static methods for common operations on brainfiles,
    serving as a convenient entry point to the library's functionality.

    Example:
        >>> from brainfile import Brainfile
        >>>
        >>> # Parse a brainfile
        >>> result = Brainfile.parse_with_errors(content)
        >>> if result.board:
        ...     print(f"Title: {result.board.title}")
        >>>
        >>> # Validate a board
        >>> validation = Brainfile.validate(result.board)
        >>> if not validation.valid:
        ...     for error in validation.errors:
        ...         print(f"Error: {error.message}")
    """

    @staticmethod
    def parse(content: str) -> dict | None:
        """
        Parse a brainfile.md file content.

        Args:
            content: The markdown content with YAML frontmatter

        Returns:
            Parsed Board object or None if parsing fails
        """
        return BrainfileParser.parse(content)

    @staticmethod
    def parse_with_errors(
        content: str,
        filename: str | None = None,
        schema_hints: SchemaHints | None = None,
    ) -> ParseResult:
        """
        Parse with detailed error reporting.

        Args:
            content: The markdown content with YAML frontmatter
            filename: Optional filename for type inference
            schema_hints: Optional schema hints for renderer inference

        Returns:
            ParseResult with board or error message
        """
        return BrainfileParser.parse_with_errors(content, filename, schema_hints)

    @staticmethod
    def serialize(
        board: Board | BrainfileUnion | dict,
        options: SerializeOptions | None = None,
    ) -> str:
        """
        Serialize a Board object back to brainfile.md format.

        Args:
            board: The Board object to serialize
            options: Optional serialization options

        Returns:
            Markdown string with YAML frontmatter
        """
        return BrainfileSerializer.serialize(board, options)

    @staticmethod
    def validate(board: object) -> ValidationResult:
        """
        Validate a Board object.

        Args:
            board: The board to validate

        Returns:
            ValidationResult with any errors found
        """
        return BrainfileValidator.validate(board)

    @staticmethod
    def lint(content: str, options: LintOptions | None = None) -> LintResult:
        """
        Lint a brainfile.md content string.

        Args:
            content: The markdown content with YAML frontmatter
            options: Linting options

        Returns:
            LintResult with issues and optionally fixed content
        """
        return BrainfileLinter.lint(content, options)

    @staticmethod
    def get_built_in_templates() -> list[TaskTemplate]:
        """
        Get all built-in templates.

        Returns:
            Array of built-in templates
        """
        return BUILT_IN_TEMPLATES

    @staticmethod
    def get_template(template_id: str) -> TaskTemplate | None:
        """
        Get a template by ID.

        Args:
            template_id: The template ID

        Returns:
            The template or None if not found
        """
        return get_template_by_id(template_id)

    @staticmethod
    def create_from_template(
        template_id: str,
        values: dict[str, str],
    ) -> dict:
        """
        Create a task from a template.

        Args:
            template_id: The template ID
            values: Variable values to substitute

        Returns:
            A partial Task object as a dict

        Raises:
            ValueError: If template not found
        """
        template = get_template_by_id(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        return process_template(template, values)

    @staticmethod
    def find_task_location(
        content: str,
        task_id: str,
    ) -> tuple[int, int] | None:
        """
        Find the location of a task in the file content.

        Args:
            content: The markdown content
            task_id: The task ID to find

        Returns:
            Tuple of (line, column) location or None if not found
        """
        return BrainfileParser.find_task_location(content, task_id)

    @staticmethod
    def find_rule_location(
        content: str,
        rule_id: int,
        rule_type: str,
    ) -> tuple[int, int] | None:
        """
        Find the location of a rule in the file content.

        Args:
            content: The markdown content
            rule_id: The rule ID to find
            rule_type: The type of rule (always, never, prefer, context)

        Returns:
            Tuple of (line, column) location or None if not found
        """
        return BrainfileParser.find_rule_location(content, rule_id, rule_type)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Version
    "__version__",
    # Main facade
    "Brainfile",
    # Enums
    "BrainfileType",
    "RendererType",
    "Priority",
    "TemplateType",
    # Type literals
    "PriorityLiteral",
    "TemplateLiteral",
    "RuleTypeLiteral",
    # Base models
    "Rule",
    "Rules",
    "AgentInstructions",
    "StatsConfig",
    "Subtask",
    "Task",
    "TaskTemplate",
    "TemplateVariable",
    "TemplateConfig",
    # Board models
    "Column",
    "Board",
    # Union type (board only in official apps)
    "BrainfileUnion",
    # Parser
    "BrainfileParser",
    "ParseResult",
    # Inference
    "infer_type",
    "infer_renderer",
    # Schema Hints
    "SchemaHints",
    "parse_schema_hints",
    "load_schema_hints",
    # Serializer
    "BrainfileSerializer",
    "SerializeOptions",
    # Validator
    "BrainfileValidator",
    "ValidationError",
    "ValidationResult",
    # Linter
    "BrainfileLinter",
    "LintIssue",
    "LintResult",
    "LintOptions",
    # Realtime
    "diff_boards",
    "hash_board",
    "hash_board_content",
    "BoardDiff",
    "ColumnDiff",
    "TaskDiff",
    # Templates
    "BUILT_IN_TEMPLATES",
    "generate_task_id",
    "generate_subtask_id",
    "process_template",
    "get_template_by_id",
    "get_all_template_ids",
    # Operations
    "BoardOperationResult",
    "BulkOperationResult",
    "BulkItemResult",
    "TaskInput",
    "TaskPatch",
    "move_task",
    "add_task",
    "update_task",
    "delete_task",
    "toggle_subtask",
    "update_board_title",
    "update_stats_config",
    "archive_task",
    "restore_task",
    "patch_task",
    "add_subtask",
    "delete_subtask",
    "update_subtask",
    "set_subtasks_completed",
    "set_all_subtasks_completed",
    "move_tasks",
    "patch_tasks",
    "delete_tasks",
    "archive_tasks",
    # Query
    "TaskInfo",
    "find_column_by_id",
    "find_column_by_name",
    "find_task_by_id",
    "task_id_exists",
    "column_exists",
    "get_all_tasks",
    "get_tasks_by_tag",
    "get_tasks_by_priority",
    "get_tasks_by_assignee",
    "search_tasks",
    "get_column_task_count",
    "get_total_task_count",
    "get_tasks_with_incomplete_subtasks",
    "get_overdue_tasks",
    # ID Generation
    "extract_task_id_number",
    "get_max_task_id_number",
    "generate_next_task_id",
    "generate_subtask_id_from_index",
    "generate_next_subtask_id",
    "is_valid_task_id",
    "is_valid_subtask_id",
    "get_parent_task_id",
    # Discovery
    "discover",
    "find_primary_brainfile",
    "find_nearest_brainfile",
    "watch_brainfiles",
    "is_brainfile_name",
    "extract_brainfile_suffix",
    "BRAINFILE_PATTERNS",
    "BRAINFILE_GLOBS",
    "EXCLUDE_DIRS",
    "DiscoveredFile",
    "DiscoveryOptions",
    "DiscoveryResult",
]
