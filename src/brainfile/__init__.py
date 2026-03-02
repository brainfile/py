"""
brainfile - Python library for the Brainfile task management protocol.

File-based task coordination for AI agents. Each task is a markdown file
with YAML frontmatter in .brainfile/board/ (active) and .brainfile/logs/ (completed).

Example:
    >>> from brainfile import ensure_dirs, add_task_file, read_tasks_dir, complete_task_file
    >>>
    >>> dirs = ensure_dirs(".brainfile/brainfile.md")
    >>> result = add_task_file(dirs.board_dir, {"title": "Ship it", "column": "todo"})
    >>> for doc in read_tasks_dir(dirs.board_dir):
    ...     print(f"{doc.task.id}: {doc.task.title}")
"""

from __future__ import annotations

__version__ = "0.2.0"

# =============================================================================
# Models
# =============================================================================

from .models import (
    AgentInstructions,
    BoardConfig,
    BrainfileType,
    ColumnConfig,
    Contract,
    ContractContext,
    ContractMetrics,
    ContractPatch,
    ContractStatus,
    Deliverable,
    Priority,
    PriorityLiteral,
    RendererType,
    Rule,
    Rules,
    RuleTypeLiteral,
    StatsConfig,
    Subtask,
    Task,
    TaskDocument,
    TaskTemplate,
    TemplateConfig,
    TemplateLiteral,
    TemplateType,
    TemplateVariable,
    TypeEntry,
    TypesConfig,
    ValidationConfig,
)

# =============================================================================
# Board Validation
# =============================================================================

from .board_validation import (
    BoardValidationResult,
    get_board_types,
    validate_column,
    validate_type,
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
    WatchError,
    WatchResult,
    discover,
    extract_brainfile_suffix,
    find_nearest_brainfile,
    find_primary_brainfile,
    is_brainfile_name,
    watch_brainfiles,
)

# =============================================================================
# Files
# =============================================================================

from .files import (
    BRAINFILE_BASENAME,
    BRAINFILE_STATE_BASENAME,
    DOT_BRAINFILE_DIRNAME,
    DOT_BRAINFILE_GITIGNORE_BASENAME,
    BrainfileResolutionKind,
    FoundBrainfile,
    ResolveBrainfilePathOptions,
    ensure_dot_brainfile_dir,
    ensure_dot_brainfile_gitignore,
    find_brainfile,
    get_brainfile_state_dir,
    get_brainfile_state_path,
    get_dot_brainfile_gitignore_path,
    resolve_brainfile_path,
)

# =============================================================================
# ID Generation
# =============================================================================

from .id_gen import (
    extract_task_id_number,
    generate_next_subtask_id,
    get_parent_task_id,
    is_valid_subtask_id,
    is_valid_task_id,
)

# =============================================================================
# Ledger
# =============================================================================

from .ledger import (
    append_ledger_record,
    build_ledger_record,
    get_file_history,
    get_task_context,
    is_ledger_contract_status,
    normalize_path_value,
    query_ledger,
    read_ledger,
)

# =============================================================================
# Inference
# =============================================================================

from .inference import infer_renderer, infer_type

# =============================================================================
# Parser
# =============================================================================

from .parser import BrainfileParser, ParseResult

# =============================================================================
# Task File I/O
# =============================================================================

from .task_file import (
    parse_task_content,
    read_task_file,
    read_tasks_dir,
    serialize_task_content,
    task_file_name,
    write_task_file,
)

# =============================================================================
# Task Operations
# =============================================================================

from .task_operations import (
    TaskFileInput,
    TaskFilters,
    TaskOperationResult,
    add_task_file,
    append_log,
    complete_task_file,
    delete_task_file,
    find_task,
    generate_next_file_task_id,
    list_tasks,
    move_task_file,
    search_logs,
    search_task_files,
)
from .types_ledger import (
    LEDGER_CONTRACT_STATUSES,
    BuildLedgerRecordOptions,
    FileHistoryOptions,
    LedgerContractStatus,
    LedgerDateRange,
    LedgerQueryFilters,
    LedgerRecord,
    LedgerRecordType,
    TaskContextEntry,
    TaskContextOptions,
)

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
# Workspace
# =============================================================================

from .workspace import (
    WorkspaceDirs,
    compose_body,
    ensure_dirs,
    extract_description,
    extract_log,
    find_task as find_workspace_task,
    get_dirs,
    get_log_file_path,
    get_task_file_path,
    is_workspace,
    read_board_config,
)

# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Version
    "__version__",
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
    # Task models
    "Task",
    "TaskDocument",
    "TaskTemplate",
    "TemplateVariable",
    "TemplateConfig",
    # Board config
    "BoardConfig",
    "ColumnConfig",
    "TypeEntry",
    "TypesConfig",
    # Contract models
    "Contract",
    "ContractStatus",
    "ContractContext",
    "ContractMetrics",
    "ContractPatch",
    "Deliverable",
    "ValidationConfig",
    # Parser
    "BrainfileParser",
    "ParseResult",
    # Inference
    "infer_type",
    "infer_renderer",
    # Templates
    "BUILT_IN_TEMPLATES",
    "generate_task_id",
    "process_template",
    "get_template_by_id",
    "get_all_template_ids",
    # Task file I/O
    "parse_task_content",
    "serialize_task_content",
    "read_task_file",
    "write_task_file",
    "read_tasks_dir",
    "task_file_name",
    # Task operations
    "generate_next_file_task_id",
    "add_task_file",
    "move_task_file",
    "complete_task_file",
    "delete_task_file",
    "append_log",
    "list_tasks",
    "find_task",
    "search_task_files",
    "search_logs",
    "TaskOperationResult",
    "TaskFileInput",
    "TaskFilters",
    # Workspace
    "WorkspaceDirs",
    "get_dirs",
    "is_workspace",
    "ensure_dirs",
    "get_task_file_path",
    "get_log_file_path",
    "find_workspace_task",
    "extract_description",
    "extract_log",
    "compose_body",
    "read_board_config",
    # Board validation
    "get_board_types",
    "validate_type",
    "validate_column",
    "BoardValidationResult",
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
    "WatchError",
    "WatchResult",
    # Files
    "find_brainfile",
    "resolve_brainfile_path",
    "get_brainfile_state_dir",
    "get_brainfile_state_path",
    "get_dot_brainfile_gitignore_path",
    "ensure_dot_brainfile_dir",
    "ensure_dot_brainfile_gitignore",
    "DOT_BRAINFILE_DIRNAME",
    "BRAINFILE_BASENAME",
    "BRAINFILE_STATE_BASENAME",
    "DOT_BRAINFILE_GITIGNORE_BASENAME",
    "FoundBrainfile",
    "BrainfileResolutionKind",
    "ResolveBrainfilePathOptions",
    # ID Generation
    "extract_task_id_number",
    "generate_subtask_id",
    "generate_next_subtask_id",
    "is_valid_task_id",
    "is_valid_subtask_id",
    "get_parent_task_id",
    # Ledger types + operations
    "LedgerRecordType",
    "LedgerContractStatus",
    "LEDGER_CONTRACT_STATUSES",
    "LedgerRecord",
    "BuildLedgerRecordOptions",
    "LedgerDateRange",
    "LedgerQueryFilters",
    "FileHistoryOptions",
    "TaskContextOptions",
    "TaskContextEntry",
    "build_ledger_record",
    "append_ledger_record",
    "read_ledger",
    "query_ledger",
    "get_file_history",
    "get_task_context",
    "normalize_path_value",
    "is_ledger_contract_status",
]
