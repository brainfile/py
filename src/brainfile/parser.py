"""
Parser for Brainfile markdown files with YAML frontmatter.

This module provides parsing functionality for brainfile.md files,
extracting YAML frontmatter and converting it to typed data structures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import StringIO
from typing import Any

from ruamel.yaml import YAML

from .inference import SchemaHints, infer_renderer, infer_type
from .models import Board, BrainfileType, Column, RendererType
from .models import Brainfile as BrainfileUnion


@dataclass
class ParseResult:
    """Result of parsing a brainfile."""

    data: BrainfileUnion | dict[str, Any] | None = None
    """Parsed brainfile data (type depends on detected type)"""

    type: str | None = None
    """Detected brainfile type"""

    renderer: RendererType | None = None
    """Inferred renderer type"""

    board: Board | None = None
    """Legacy board accessor (deprecated, use data instead)"""

    error: str | None = None
    """Error message if parsing failed"""

    warnings: list[str] | None = None
    """Warning messages from parser"""


def _create_yaml() -> YAML:
    """
    Create a configured YAML instance for parsing.

    Configures the ruamel.yaml YAML instance with appropriate settings
    for brainfile parsing, including quote preservation and block style.

    Returns:
        Configured YAML instance ready for parsing brainfile content
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    return yaml


def _consolidate_duplicate_columns(
    columns: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Consolidate duplicate columns by merging their tasks.

    Args:
        columns: Array of columns that may contain duplicates

    Returns:
        Tuple of (deduplicated columns, warning messages)
    """
    warnings: list[str] = []
    column_map: dict[str, dict[str, Any]] = {}

    for column in columns:
        column_id = column.get("id", "")
        existing = column_map.get(column_id)

        if existing:
            # Duplicate found - merge tasks
            task_count = len(column.get("tasks", []))
            warnings.append(
                f'Duplicate column detected: "{column_id}" '
                f'(title: "{column.get("title", "")}"). '
                f"Merging {task_count} task(s) into existing column."
            )

            # Merge tasks from duplicate column into existing column
            existing_tasks = existing.get("tasks", [])
            new_tasks = column.get("tasks", [])
            existing["tasks"] = existing_tasks + new_tasks
        else:
            # First occurrence of this column ID
            column_map[column_id] = column

    return list(column_map.values()), warnings


class BrainfileParser:
    """Parser for Brainfile markdown files with YAML frontmatter."""

    @staticmethod
    def parse(content: str) -> dict[str, Any] | None:
        """
        Parse a brainfile.md file content.

        Args:
            content: The markdown content with YAML frontmatter

        Returns:
            Parsed brainfile data or None if parsing fails

        Note:
            Deprecated: Use parse_with_errors() for type detection and error details
        """
        try:
            # Extract YAML frontmatter
            lines = content.split("\n")

            # Check for frontmatter start
            if not lines[0].strip().startswith("---"):
                return None

            # Find frontmatter end
            end_index = -1
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    end_index = i
                    break

            if end_index == -1:
                return None

            # Extract YAML content
            yaml_content = "\n".join(lines[1:end_index])

            # Parse YAML
            yaml = _create_yaml()
            data = yaml.load(StringIO(yaml_content))

            if data is None:
                return None

            # Convert to regular dict for easier manipulation
            data = dict(data) if hasattr(data, "items") else data

            # Consolidate duplicate columns (for board type compatibility)
            if data and isinstance(data.get("columns"), list):
                columns, warnings = _consolidate_duplicate_columns(data["columns"])

                # Log warnings to console
                if warnings:
                    import sys

                    print("[Brainfile Parser] Duplicate columns detected:", file=sys.stderr)
                    for warning in warnings:
                        print(f"  - {warning}", file=sys.stderr)

                data["columns"] = columns

            return data

        except Exception as e:
            import sys

            print(f"Error parsing brainfile.md: {e}", file=sys.stderr)
            return None

    @staticmethod
    def parse_with_errors(
        content: str,
        filename: str | None = None,
        schema_hints: SchemaHints | None = None,
    ) -> ParseResult:
        """
        Parse with detailed error reporting, warnings, and type detection.

        Args:
            content: The markdown content with YAML frontmatter
            filename: Optional filename for type inference
            schema_hints: Optional schema hints for renderer inference

        Returns:
            ParseResult with data, type, renderer, error message, and any warnings
        """
        warnings: list[str] = []
        captured_warnings: list[str] = []

        # We'll capture warnings differently since Python doesn't have console.warn
        # Instead, we track them internally

        try:
            # Parse content and capture any duplicate column warnings
            data = BrainfileParser._parse_with_warning_capture(content, captured_warnings)

            warnings.extend(captured_warnings)

            if data is None:
                return ParseResult(
                    data=None,
                    board=None,
                    error="Failed to parse YAML frontmatter",
                    warnings=warnings if warnings else None,
                )

            # Infer type and renderer
            detected_type = infer_type(data, filename)
            renderer = infer_renderer(detected_type, data, schema_hints)

            # Determine if this is a board type
            is_board = detected_type == BrainfileType.BOARD.value or (
                not data.get("type") and isinstance(data.get("columns"), list)
            )

            board: Board | None = None
            if is_board:
                try:
                    board = Board.model_validate(data)
                except Exception:
                    # If validation fails, still return the raw data
                    pass

            return ParseResult(
                data=board if board else data,
                type=detected_type,
                renderer=renderer,
                board=board,
                warnings=warnings if warnings else None,
            )

        except Exception as e:
            return ParseResult(
                data=None,
                board=None,
                error=str(e),
                warnings=warnings if warnings else None,
            )

    @staticmethod
    def _parse_with_warning_capture(
        content: str,
        warnings: list[str],
    ) -> dict[str, Any] | None:
        """
        Parse content and capture duplicate column warnings.

        Args:
            content: The markdown content with YAML frontmatter
            warnings: List to append warnings to

        Returns:
            Parsed data or None
        """
        try:
            # Extract YAML frontmatter
            lines = content.split("\n")

            # Check for frontmatter start
            if not lines[0].strip().startswith("---"):
                return None

            # Find frontmatter end
            end_index = -1
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    end_index = i
                    break

            if end_index == -1:
                return None

            # Extract YAML content
            yaml_content = "\n".join(lines[1:end_index])

            # Parse YAML
            yaml = _create_yaml()
            data = yaml.load(StringIO(yaml_content))

            if data is None:
                return None

            # Convert to regular dict
            data = dict(data) if hasattr(data, "items") else data

            # Consolidate duplicate columns
            if data and isinstance(data.get("columns"), list):
                columns, column_warnings = _consolidate_duplicate_columns(data["columns"])

                # Add warnings with proper formatting
                if column_warnings:
                    warnings.append("[Brainfile Parser] Duplicate columns detected:")
                    for warning in column_warnings:
                        warnings.append(f"  - {warning}")

                data["columns"] = columns

            return data

        except Exception:
            return None

    @staticmethod
    def find_task_location(
        content: str,
        task_id: str,
    ) -> tuple[int, int] | None:
        """
        Find the line number of a task in the file.

        Args:
            content: The markdown content
            task_id: The task ID to find

        Returns:
            Tuple of (line, column) location or None if not found.
            Line numbers are 1-indexed for editor compatibility.
        """
        lines = content.split("\n")

        for i, line in enumerate(lines):
            # Look for lines that contain the task ID
            if f"id: {task_id}" in line:
                # Check if this line starts with a dash followed by id
                # (standard format: - id: task-N)
                if re.match(r"^\s*-\s+id:\s+", line):
                    return (i + 1, 0)  # +1 because editors are typically 1-indexed

                # Check if the id is on the next line after a dash
                # (alternative format)
                if i > 0 and re.match(r"^\s*-\s*$", lines[i - 1]):
                    return (i, 0)  # Return the dash line

                # Default to the line with the id
                return (i + 1, 0)

        return None

    @staticmethod
    def find_rule_location(
        content: str,
        rule_id: int,
        rule_type: str,
    ) -> tuple[int, int] | None:
        """
        Find the line number of a rule in the YAML frontmatter.

        Args:
            content: The markdown content
            rule_id: The rule ID to find
            rule_type: The type of rule (always, never, prefer, context)

        Returns:
            Tuple of (line, column) location or None if not found.
            Line numbers are 1-indexed for editor compatibility.
        """
        lines = content.split("\n")
        in_frontmatter = False
        in_rules_section = False
        in_rule_type_section = False

        for i, line in enumerate(lines):
            trimmed_line = line.strip()

            # Check for frontmatter boundaries
            if trimmed_line == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    # End of frontmatter
                    break

            if not in_frontmatter:
                continue

            # Check if we're in the rules section
            if trimmed_line == "rules:":
                in_rules_section = True
                continue

            # Check if we're in the specific rule type section
            if in_rules_section and trimmed_line == f"{rule_type}:":
                in_rule_type_section = True
                continue

            # If we hit another top-level key, we've left the rules section
            if in_rules_section and re.match(r"^[a-z]+:", line) and not re.match(r"^\s", line):
                in_rules_section = False
                in_rule_type_section = False

            # If we're in the rule type section, look for the rule with matching ID
            if in_rule_type_section:
                # Check if this is a new rule type section within rules
                if re.match(r"^\s{2}[a-z]+:", line) and f"{rule_type}:" not in line:
                    in_rule_type_section = False
                    continue

                # Look for the rule ID
                if f"id: {rule_id}" in line:
                    # Check if this line starts with a dash followed by id
                    # (compact format: - id: N)
                    if re.match(r"^\s*-\s+id:\s+", line):
                        return (i + 1, 0)  # +1 for 1-indexed

                    # Check if the id is on the next line after a dash
                    # (expanded format)
                    if i > 0 and re.match(r"^\s*-\s*$", lines[i - 1]):
                        return (i, 0)  # Return the dash line

                    # Default to the line with the id
                    return (i + 1, 0)

        return None
