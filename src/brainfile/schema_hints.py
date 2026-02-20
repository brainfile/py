"""
Schema hints parser for x-brainfile-* JSON Schema extensions.

This module provides functionality to parse x-brainfile-* extensions from
JSON Schema objects, allowing schema authors to specify rendering hints
and field mappings for custom brainfile types.

Supported extensions:
- x-brainfile-renderer: Force specific renderer (kanban, timeline, checklist, tree)
- x-brainfile-columns-path: JSONPath to column-like array
- x-brainfile-items-path: JSONPath to item arrays
- x-brainfile-title-field: Field to use as item title
- x-brainfile-status-field: Field for status/completion
- x-brainfile-timestamp-field: Field for timestamps
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any


@dataclass
class SchemaHints:
    """
    Schema hints extracted from JSON Schema x-brainfile-* extensions.

    These hints allow schema authors to customize how brainfile apps
    should render and interpret custom schemas.
    """

    renderer: str | None = None
    """Preferred renderer (kanban, timeline, checklist, tree, etc.)"""

    columns_path: str | None = None
    """JSONPath to columns array (e.g., '$.columns')"""

    items_path: str | None = None
    """JSONPath to items arrays (e.g., '$.columns[*].tasks')"""

    title_field: str | None = None
    """Field to use as item title"""

    status_field: str | None = None
    """Field to use for status/completion"""

    timestamp_field: str | None = None
    """Field to use for timestamps"""


def parse_schema_hints(schema: dict[str, Any] | None) -> SchemaHints:
    """
    Parse x-brainfile-* extensions from a JSON Schema object.

    Extracts brainfile-specific hints from a JSON Schema that uses
    x-brainfile-* extension properties. These hints are used by
    brainfile apps to determine how to render custom schemas.

    Args:
        schema: JSON Schema object (can be loaded from URL or inline).
                If None or not a dict, returns empty hints.

    Returns:
        SchemaHints dataclass with extracted values.
        Missing extensions result in None for those fields.

    Example:
        >>> schema = {
        ...     "$schema": "https://json-schema.org/draft/2020-12/schema",
        ...     "x-brainfile-renderer": "kanban",
        ...     "x-brainfile-columns-path": "$.columns"
        ... }
        >>> hints = parse_schema_hints(schema)
        >>> hints.renderer
        'kanban'
    """
    hints = SchemaHints()

    if not schema or not isinstance(schema, dict):
        return hints

    # Parse x-brainfile-renderer
    renderer = schema.get("x-brainfile-renderer")
    if renderer and isinstance(renderer, str):
        hints.renderer = renderer

    # Parse x-brainfile-columns-path
    columns_path = schema.get("x-brainfile-columns-path")
    if columns_path and isinstance(columns_path, str):
        hints.columns_path = columns_path

    # Parse x-brainfile-items-path
    items_path = schema.get("x-brainfile-items-path")
    if items_path and isinstance(items_path, str):
        hints.items_path = items_path

    # Parse x-brainfile-title-field
    title_field = schema.get("x-brainfile-title-field")
    if title_field and isinstance(title_field, str):
        hints.title_field = title_field

    # Parse x-brainfile-status-field
    status_field = schema.get("x-brainfile-status-field")
    if status_field and isinstance(status_field, str):
        hints.status_field = status_field

    # Parse x-brainfile-timestamp-field
    timestamp_field = schema.get("x-brainfile-timestamp-field")
    if timestamp_field and isinstance(timestamp_field, str):
        hints.timestamp_field = timestamp_field

    return hints


def load_schema_hints(schema_url: str) -> SchemaHints | None:
    """
    Load schema from URL and parse hints.

    Fetches a JSON Schema from the specified URL and extracts
    x-brainfile-* extension hints. Uses synchronous HTTP request
    via urllib for simplicity.

    Args:
        schema_url: URL to JSON Schema file

    Returns:
        SchemaHints if successful, None on any error (network, parsing, etc.)

    Note:
        This function catches all exceptions and returns None on failure,
        logging warnings to stderr. This is intentional as schema hints
        are optional and should not break parsing if unavailable.

    Example:
        >>> hints = load_schema_hints("https://example.com/schema.json")
        >>> if hints:
        ...     print(f"Renderer: {hints.renderer}")
    """
    try:
        request = urllib.request.Request(
            schema_url,
            headers={"Accept": "application/json", "User-Agent": "brainfile-py/0.1.0"},
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 200:
                import sys
                print(
                    f"Warning: Failed to load schema from {schema_url}: HTTP {response.status}",
                    file=sys.stderr,
                )
                return None

            content = response.read().decode("utf-8")
            schema = json.loads(content)
            return parse_schema_hints(schema)

    except urllib.error.URLError as e:
        import sys
        print(f"Warning: Failed to load schema from {schema_url}: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        import sys
        print(f"Warning: Invalid JSON in schema from {schema_url}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        import sys
        print(f"Warning: Error loading schema from {schema_url}: {e}", file=sys.stderr)
        return None
