"""
Type and renderer inference logic.

This module provides functions to infer brainfile type and renderer
from various signals including explicit type fields, schema URLs,
filenames, and structural analysis.

Note: While this module can detect various types for compatibility,
the official brainfile apps only support the board type.
"""

from __future__ import annotations

from typing import Any

from .models import BrainfileType, RendererType
from .schema_hints import SchemaHints


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
    # 1. Explicit type field
    if isinstance(data, dict) and data.get("type") and isinstance(data["type"], str):
        return data["type"]

    # 2. Schema URL pattern
    if isinstance(data, dict):
        schema = data.get("schema")
        if schema and isinstance(schema, str):
            import re

            match = re.search(r"/v1/(\w+)\.json$", schema)
            if match:
                return match.group(1)

    # 3. File name suffix (brainfile.TYPE.md)
    if filename:
        import re

        match = re.search(r"brainfile\.(\w+)\.md$", filename)
        if match:
            return match.group(1)

    # 4. Structure analysis
    detected_type = _detect_type_from_structure(data)
    if detected_type:
        return detected_type

    # 5. Default
    return BrainfileType.BOARD.value


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

    # Check for journal structure (entries array)
    if isinstance(data.get("entries"), list):
        return BrainfileType.JOURNAL.value

    # Check for board structure (columns array)
    if isinstance(data.get("columns"), list):
        return BrainfileType.BOARD.value

    # Check for collection structure (categories array)
    if isinstance(data.get("categories"), list):
        return BrainfileType.COLLECTION.value

    # Check for checklist structure (flat items array with completed)
    items = data.get("items")
    if isinstance(items, list) and len(items) > 0:
        has_completed = all(
            isinstance(item, dict) and isinstance(item.get("completed"), bool)
            for item in items
        )
        if has_completed:
            return BrainfileType.CHECKLIST.value

    # Check for document structure (sections array)
    if isinstance(data.get("sections"), list):
        return BrainfileType.DOCUMENT.value

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
    # 1. Schema hint (explicit override)
    if schema_hints and schema_hints.renderer:
        try:
            return RendererType(schema_hints.renderer)
        except ValueError:
            pass  # Invalid renderer hint, continue to structural detection

    # 2. Structural pattern matching (universal code path)
    renderer_from_structure = _detect_renderer_from_structure(data)
    if renderer_from_structure:
        return renderer_from_structure

    # 3. Fallback
    return RendererType.TREE


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

    # Columns with nested items -> kanban
    if isinstance(data.get("columns"), list):
        return RendererType.KANBAN

    # Entries with timestamps -> timeline
    entries = data.get("entries")
    if isinstance(entries, list) and len(entries) > 0:
        has_timestamps = any(
            isinstance(entry, dict)
            and (entry.get("createdAt") or entry.get("timestamp"))
            for entry in entries
        )
        if has_timestamps:
            return RendererType.TIMELINE

    # Items with completed boolean -> checklist
    items = data.get("items")
    if isinstance(items, list) and len(items) > 0:
        has_completed = all(
            isinstance(item, dict) and isinstance(item.get("completed"), bool)
            for item in items
        )
        if has_completed:
            return RendererType.CHECKLIST

    # Categories with nested items -> grouped-list
    if isinstance(data.get("categories"), list):
        return RendererType.GROUPED_LIST

    # Sections array -> document
    if isinstance(data.get("sections"), list):
        return RendererType.DOCUMENT

    return None
