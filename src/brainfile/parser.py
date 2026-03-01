"""
Parser for Brainfile markdown files with YAML frontmatter.

This module provides parsing functionality for brainfile.md files,
extracting YAML frontmatter and converting it to typed data structures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import StringIO
from typing import Any

from .inference import SchemaHints, infer_renderer, infer_type
from .models import BrainfileType, RendererType
from ._yaml import create_yaml


@dataclass
class ParseResult:
    """Result of parsing a brainfile."""

    data: dict[str, Any] | None = None
    """Parsed frontmatter data"""

    type: str | None = None
    """Detected brainfile type"""

    renderer: RendererType | None = None
    """Inferred renderer type"""

    error: str | None = None
    """Error message if parsing failed"""

    warnings: list[str] | None = None
    """Warning messages from parser"""


def _consolidate_duplicate_columns(
    columns: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Consolidate duplicate columns by merging their tasks."""
    warnings: list[str] = []
    column_map: dict[str, dict[str, Any]] = {}

    for column in columns:
        column_id = column.get("id", "")
        existing = column_map.get(column_id)

        if existing:
            task_count = len(column.get("tasks", []))
            warnings.append(
                f'Duplicate column detected: "{column_id}" '
                f'(title: "{column.get("title", "")}"). '
                f"Merging {task_count} task(s) into existing column."
            )
            existing_tasks = existing.get("tasks", [])
            new_tasks = column.get("tasks", [])
            existing["tasks"] = existing_tasks + new_tasks
        else:
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
            Parsed data as dict or None if parsing fails
        """
        warnings: list[str] = []
        data = BrainfileParser._parse_with_warning_capture(content, warnings)
        if warnings:
            import sys
            for warning in warnings:
                print(warning, file=sys.stderr)
        return data

    @staticmethod
    def parse_with_errors(
        content: str,
        filename: str | None = None,
        schema_hints: SchemaHints | None = None,
    ) -> ParseResult:
        """Parse with detailed error reporting, warnings, and type detection."""
        warnings: list[str] = []
        captured_warnings: list[str] = []

        try:
            data = BrainfileParser._parse_with_warning_capture(content, captured_warnings)
            warnings.extend(captured_warnings)

            if data is None:
                return ParseResult(
                    data=None,
                    error="Failed to parse YAML frontmatter",
                    warnings=warnings if warnings else None,
                )

            detected_type = infer_type(data, filename)
            renderer = infer_renderer(detected_type, data, schema_hints)

            return ParseResult(
                data=data,
                type=detected_type,
                renderer=renderer,
                warnings=warnings if warnings else None,
            )

        except Exception as e:
            return ParseResult(
                data=None,
                error=str(e),
                warnings=warnings if warnings else None,
            )

    @staticmethod
    def _parse_with_warning_capture(
        content: str,
        warnings: list[str],
    ) -> dict[str, Any] | None:
        """Parse content and capture duplicate column warnings."""
        try:
            lines = content.split("\n")

            if not lines[0].strip().startswith("---"):
                return None

            end_index = -1
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    end_index = i
                    break

            if end_index == -1:
                return None

            yaml_content = "\n".join(lines[1:end_index])
            yaml = create_yaml()
            data = yaml.load(StringIO(yaml_content))

            if data is None:
                return None

            data = dict(data) if hasattr(data, "items") else data

            if data and isinstance(data.get("columns"), list):
                columns, column_warnings = _consolidate_duplicate_columns(data["columns"])
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
        """Find the line number of a task in the file."""
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if f"id: {task_id}" in line:
                if re.match(r"^\s*-\s+id:\s+", line):
                    return (i + 1, 0)
                if i > 0 and re.match(r"^\s*-\s*$", lines[i - 1]):
                    return (i, 0)
                return (i + 1, 0)

        return None

    @staticmethod
    def find_rule_location(
        content: str,
        rule_id: int,
        rule_type: str,
    ) -> tuple[int, int] | None:
        """Find the line number of a rule in the YAML frontmatter."""
        lines = content.split("\n")
        in_frontmatter = False
        in_rules_section = False
        in_rule_type_section = False

        for i, line in enumerate(lines):
            trimmed_line = line.strip()

            if trimmed_line == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    break

            if not in_frontmatter:
                continue

            if trimmed_line == "rules:":
                in_rules_section = True
                continue

            if in_rules_section and trimmed_line == f"{rule_type}:":
                in_rule_type_section = True
                continue

            if in_rules_section and re.match(r"^[a-z]+:", line) and not re.match(r"^\s", line):
                in_rules_section = False
                in_rule_type_section = False

            if in_rule_type_section:
                if re.match(r"^\s{2}[a-z]+:", line) and f"{rule_type}:" not in line:
                    in_rule_type_section = False
                    continue

                if f"id: {rule_id}" in line:
                    if re.match(r"^\s*-\s+id:\s+", line):
                        return (i + 1, 0)
                    if i > 0 and re.match(r"^\s*-\s*$", lines[i - 1]):
                        return (i, 0)
                    return (i + 1, 0)

        return None
