"""snake_case <-> camelCase key conversion helpers.

These are used to translate between Python-style snake_case attribute names and
the camelCase keys expected by the brainfile JSON/YAML wire format.
"""

from __future__ import annotations

import re
from typing import Any

# Pre-compiled regex for camelCase -> snake_case
_CAMEL_TO_SNAKE_RE = re.compile(r"(?<=[a-z0-9])([A-Z])")

# Explicit mapping for known aliases (snake -> camel)
_SNAKE_TO_CAMEL: dict[str, str] = {
    "parent_id": "parentId",
    "related_files": "relatedFiles",
    "due_date": "dueDate",
    "created_at": "createdAt",
    "updated_at": "updatedAt",
    "completed_at": "completedAt",
    "file_path": "filePath",
    "completion_column": "completionColumn",
    "id_prefix": "idPrefix",
    "schema_url": "schema",
    "llm_notes": "llmNotes",
    "stats_config": "statsConfig",
    "is_built_in": "isBuiltIn",
    "default_value": "defaultValue",
    "built_in_templates": "builtInTemplates",
    "user_templates": "userTemplates",
    "out_of_scope": "outOfScope",
    "relevant_files": "relevantFiles",
    "picked_up_at": "pickedUpAt",
    "delivered_at": "deliveredAt",
    "rework_count": "reworkCount",
    "files_changed": "filesChanged",
    "column_history": "columnHistory",
    "cycle_time_hours": "cycleTimeHours",
    "contract_status": "contractStatus",
    "validation_attempts": "validationAttempts",
    "subtasks_completed": "subtasksCompleted",
    "subtasks_total": "subtasksTotal",
    "matched_files": "matchedFiles",
    "date_range": "dateRange",
    "from_": "from",
}

# Reverse mapping (camel -> snake)
_CAMEL_TO_SNAKE_MAP: dict[str, str] = {v: k for k, v in _SNAKE_TO_CAMEL.items()}


def snake_to_camel(key: str) -> str:
    """Convert a snake_case key to camelCase.

    Uses the explicit mapping first, then falls back to algorithmic conversion.
    """
    if key in _SNAKE_TO_CAMEL:
        return _SNAKE_TO_CAMEL[key]
    # Algorithmic fallback: split on underscores
    parts = key.split("_")
    if len(parts) == 1:
        return key
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def camel_to_snake(key: str) -> str:
    """Convert a camelCase key to snake_case.

    Uses the explicit mapping first, then falls back to algorithmic conversion.
    """
    if key in _CAMEL_TO_SNAKE_MAP:
        return _CAMEL_TO_SNAKE_MAP[key]
    # Algorithmic fallback
    return _CAMEL_TO_SNAKE_RE.sub(r"_\1", key).lower()


def keys_to_camel(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively convert all dict keys from snake_case to camelCase."""
    result: dict[str, Any] = {}
    for key, value in d.items():
        camel_key = snake_to_camel(key)
        if isinstance(value, dict):
            result[camel_key] = keys_to_camel(value)
        elif isinstance(value, list):
            result[camel_key] = [
                keys_to_camel(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[camel_key] = value
    return result


def keys_to_snake(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively convert all dict keys from camelCase to snake_case."""
    result: dict[str, Any] = {}
    for key, value in d.items():
        snake_key = camel_to_snake(key)
        if isinstance(value, dict):
            result[snake_key] = keys_to_snake(value)
        elif isinstance(value, list):
            result[snake_key] = [
                keys_to_snake(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[snake_key] = value
    return result
