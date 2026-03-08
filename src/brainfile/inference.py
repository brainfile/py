"""
Type and renderer inference logic.

This module provides functions to infer brainfile type and renderer
from various signals including explicit type fields, schema URLs,
filenames, and structural analysis.

Note: While this module can detect various types for compatibility,
the official brainfile apps only support the board type.
"""

from __future__ import annotations

import re
from typing import Any

from .models import BrainfileType, RendererType
from .schema_hints import SchemaHints

_SCHEMA_TYPE_RE = re.compile(r"/v1/(\w+)\.json$")
_FILENAME_TYPE_RE = re.compile(r"brainfile\.(\w+)\.md$")


def _type_from_explicit_field(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None

    type_value = data.get("type")
    return type_value if isinstance(type_value, str) and type_value else None


def _type_from_schema(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None

    schema = data.get("schema")
    if not isinstance(schema, str) or not schema:
        return None

    match = _SCHEMA_TYPE_RE.search(schema)
    return match.group(1) if match else None


def _type_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None

    match = _FILENAME_TYPE_RE.search(filename)
    return match.group(1) if match else None


def infer_type(data: Any, filename: str | None = None) -> str:
    """
    Infer brainfile type from various signals.

    Priority order:
    1. Explicit type field in frontmatter
    2. Schema URL pattern (e.g., /v1/journal.json -> journal)
    3. File name suffix (e.g., brainfile.journal.md -> journal)
    4. Structure analysis (detect required fields)
    5. Default to 'board'

    Args:
        data: Parsed frontmatter data
        filename: Optional filename for suffix detection

    Returns:
        The inferred brainfile type
    """
    return (
        _type_from_explicit_field(data)
        or _type_from_schema(data)
        or _type_from_filename(filename)
        or _detect_type_from_structure(data)
        or BrainfileType.BOARD.value
    )


def _check_list_field(data: dict[str, Any], field_name: str, brainfile_type: BrainfileType) -> str | None:
    return brainfile_type.value if isinstance(data.get(field_name), list) else None


def _is_checklist_items(items: Any) -> bool:
    return isinstance(items, list) and len(items) > 0 and all(
        isinstance(item, dict) and isinstance(item.get("completed"), bool)
        for item in items
    )


def _detect_type_from_structure(data: Any) -> str | None:
    """
    Detect brainfile type from data structure.

    Looks for type-specific required fields.

    Args:
        data: Parsed frontmatter data

    Returns:
        The detected type or None if unknown
    """
    if not isinstance(data, dict):
        return None

    return (
        _check_list_field(data, "entries", BrainfileType.JOURNAL)
        or _check_list_field(data, "columns", BrainfileType.BOARD)
        or _check_list_field(data, "categories", BrainfileType.COLLECTION)
        or (BrainfileType.CHECKLIST.value if _is_checklist_items(data.get("items")) else None)
        or _check_list_field(data, "sections", BrainfileType.DOCUMENT)
    )


def _renderer_from_schema_hints(
    schema_hints: SchemaHints | None,
) -> RendererType | None:
    if not schema_hints or not schema_hints.renderer:
        return None

    try:
        return RendererType(schema_hints.renderer)
    except ValueError:
        return None


def infer_renderer(
    type_: str,
    data: Any,
    schema_hints: SchemaHints | None = None,
) -> RendererType:
    """
    Infer renderer type from brainfile data and schema hints.

    Pure structural inference - no special treatment for official types.
    Custom types with identical structure render identically.

    Priority order:
    1. Schema hint (x-brainfile-renderer in loaded schema) - explicit override
    2. Structural pattern matching - detect from data shape
    3. Fallback to tree view

    Args:
        type_: The brainfile type (informational only, not used for inference)
        data: Parsed frontmatter data for structural analysis
        schema_hints: Optional schema hints from loaded schema

    Returns:
        The inferred renderer type
    """
    del type_

    return _renderer_from_schema_hints(schema_hints) or _detect_renderer_from_structure(data) or RendererType.TREE


def _has_timeline_entries(entries: Any) -> bool:
    return isinstance(entries, list) and len(entries) > 0 and any(
        isinstance(entry, dict) and (entry.get("createdAt") or entry.get("timestamp"))
        for entry in entries
    )


def _detect_renderer_from_structure(data: Any) -> RendererType | None:
    """
    Detect renderer from data structure patterns.

    Args:
        data: Parsed frontmatter data

    Returns:
        The detected renderer or None if unknown
    """
    if not isinstance(data, dict):
        return None

    if isinstance(data.get("columns"), list):
        return RendererType.KANBAN
    if _has_timeline_entries(data.get("entries")):
        return RendererType.TIMELINE
    if _is_checklist_items(data.get("items")):
        return RendererType.CHECKLIST
    if isinstance(data.get("categories"), list):
        return RendererType.GROUPED_LIST
    if isinstance(data.get("sections"), list):
        return RendererType.DOCUMENT
    return None
