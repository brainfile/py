from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import Any

from .frontmatter import load_frontmatter_mapping
from .inference import SchemaHints, infer_renderer, infer_type
from .models import RendererType

__all__ = ["ParseResult", "BrainfileParser"]


@dataclass
class ParseResult:
    data: dict[str, Any] | None = None
    type: str | None = None
    renderer: RendererType | None = None
    error: str | None = None
    warnings: list[str] | None = None


def _consolidate_duplicate_columns(columns: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    seen: dict[str, dict[str, Any]] = {}

    for column in columns:
        column_id = column.get("id", "")
        tasks = column.get("tasks") if isinstance(column.get("tasks"), list) else []

        if column_id not in seen:
            seen[column_id] = column
            continue

        warnings.append(
            f'Duplicate column detected: "{column_id}" '
            f'(title: "{column.get("title", "")}"). '
            f"Merging {len(tasks)} task(s) into existing column."
        )
        existing = seen[column_id].get("tasks") if isinstance(seen[column_id].get("tasks"), list) else []
        seen[column_id]["tasks"] = [*existing, *tasks]

    return list(seen.values()), warnings


def _format_duplicate_column_warnings(warnings: list[str]) -> list[str]:
    if not warnings:
        return []
    return ["[Brainfile Parser] Duplicate columns detected:", *(f"  - {warning}" for warning in warnings)]


def _find_list_item_location(lines: list[str], index: int) -> tuple[int, int]:
    line = lines[index]
    previous_is_dash = index > 0 and re.match(r"^\s*-\s*$", lines[index - 1])
    if re.match(r"^\s*-\s+id:\s+", line) or not previous_is_dash:
        return index + 1, 0
    return index, 0


def _load_and_normalize_board_data(content: str, warnings: list[str]) -> dict[str, Any] | None:
    data = load_frontmatter_mapping(content)
    if data is None:
        return None

    columns = data.get("columns")
    if isinstance(columns, list):
        merged_columns, duplicate_warnings = _consolidate_duplicate_columns(columns)
        warnings.extend(_format_duplicate_column_warnings(duplicate_warnings))
        data["columns"] = merged_columns

    return data


def _find_frontmatter_end(lines: list[str]) -> int | None:
    in_frontmatter = False
    for index, line in enumerate(lines):
        if line.strip() != "---":
            continue
        if not in_frontmatter:
            in_frontmatter = True
            continue
        return index
    return None


def _is_top_level_yaml_key(line: str) -> bool:
    return bool(re.match(r"^[a-z]+:", line) and not re.match(r"^\s", line))


def _is_other_rule_section(line: str, rule_type: str) -> bool:
    return bool(re.match(r"^\s{2}[a-z]+:", line) and f"{rule_type}:" not in line)


def _iter_rules_section(lines: list[str], rule_type: str, end_index: int) -> list[tuple[int, str]]:
    matches: list[tuple[int, str]] = []
    in_rules = False
    in_rule_section = False

    for index in range(end_index):
        line = lines[index]
        stripped = line.strip()

        in_rules, in_rule_section = _advance_rule_scan_state(
            line,
            stripped,
            rule_type,
            in_rules,
            in_rule_section,
        )
        if not in_rule_section:
            continue

        matches.append((index, line))

    return matches


def _advance_rule_scan_state(
    line: str,
    stripped: str,
    rule_type: str,
    in_rules: bool,
    in_rule_section: bool,
) -> tuple[bool, bool]:
    if stripped == "rules:":
        return True, False

    if in_rules and stripped == f"{rule_type}:":
        return True, True

    if in_rules and _is_top_level_yaml_key(line):
        return False, False

    if not in_rule_section:
        return in_rules, False

    if _is_other_rule_section(line, rule_type):
        return in_rules, False

    return in_rules, True


def _parse_board_data(content: str) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    data = _load_and_normalize_board_data(content, warnings)
    return data, warnings


def _build_parse_result(
    data: dict[str, Any],
    filename: str | None,
    schema_hints: SchemaHints | None,
    warnings: list[str],
) -> ParseResult:
    detected_type = infer_type(data, filename)
    renderer = infer_renderer(detected_type, data, schema_hints)
    return ParseResult(data, detected_type, renderer, None, warnings or None)


class BrainfileParser:
    @staticmethod
    def parse(content: str) -> dict[str, Any] | None:
        warnings: list[str] = []
        data = _load_and_normalize_board_data(content, warnings)
        for warning in warnings:
            print(warning, file=sys.stderr)
        return data

    @staticmethod
    def parse_with_errors(
        content: str,
        filename: str | None = None,
        schema_hints: SchemaHints | None = None,
    ) -> ParseResult:
        try:
            data, warnings = _parse_board_data(content)
            if data is None:
                return ParseResult(
                    None,
                    None,
                    None,
                    "Failed to parse YAML frontmatter",
                    warnings or None,
                )
            return _build_parse_result(data, filename, schema_hints, warnings)
        except Exception as exc:
            return ParseResult(error=str(exc))

    @staticmethod
    def find_task_location(content: str, task_id: str) -> tuple[int, int] | None:
        lines = content.split("\n")
        needle = f"id: {task_id}"
        for index, line in enumerate(lines):
            if needle in line:
                return _find_list_item_location(lines, index)
        return None

    @staticmethod
    def find_rule_location(content: str, rule_id: int, rule_type: str) -> tuple[int, int] | None:
        lines = content.split("\n")
        end_index = _find_frontmatter_end(lines)
        if end_index is None:
            return None

        needle = f"id: {rule_id}"
        for index, line in _iter_rules_section(lines, rule_type, end_index):
            if needle in line:
                return _find_list_item_location(lines, index)

        return None
