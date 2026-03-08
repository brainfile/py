from __future__ import annotations

from io import StringIO
from typing import Any

from ._yaml import create_yaml

__all__ = [
    "extract_frontmatter_sections",
    "has_frontmatter_start",
    "load_frontmatter_mapping",
    "trim_leading_blank_line",
]


def has_frontmatter_start(content: str) -> bool:
    lines = content.split("\n", 1)
    return bool(lines) and lines[0].strip() == "---"


def _find_frontmatter_close_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return index
    return None


def _split_frontmatter_content(content: str) -> tuple[list[str], int] | None:
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None

    close_index = _find_frontmatter_close_index(lines)
    if close_index is None:
        return None

    return lines, close_index


def extract_frontmatter_sections(content: str) -> tuple[str, str] | None:
    extracted = _split_frontmatter_content(content)
    if extracted is None:
        return None

    lines, close_index = extracted
    yaml_content = "\n".join(lines[1:close_index])
    body_content = "\n".join(lines[close_index + 1 :])
    return yaml_content, body_content


def load_frontmatter_mapping(content: str) -> dict[str, Any] | None:
    sections = extract_frontmatter_sections(content)
    if sections is None:
        return None

    yaml_content, _ = sections
    data = create_yaml().load(StringIO(yaml_content))
    if data is None or not hasattr(data, "items"):
        return None
    return dict(data)


def trim_leading_blank_line(body: str) -> str:
    return body[1:] if body.startswith("\n") else body
