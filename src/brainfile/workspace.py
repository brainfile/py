"""brainfile.workspace

Workspace detection, path resolution, and body helpers.

This mirrors TS core ``workspace.ts``.

Key concepts
- Uses a ``.brainfile/`` directory.
- Config lives at ``.brainfile/brainfile.md``.
- Active tasks live in ``.brainfile/board/*.md``.
- Completed tasks live in ``.brainfile/logs/*.md``.

All functions are side-effect free except for :func:`ensure_dirs`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from ._yaml import create_yaml
from .frontmatter import (
    extract_frontmatter_sections,
    has_frontmatter_start,
    trim_leading_blank_line,
)
from .models import BoardConfig
from .parser import BrainfileParser
from .task_file import read_task_file, read_tasks_dir, task_file_name


@dataclass(frozen=True)
class WorkspaceDirs:
    dot_dir: str
    board_dir: str
    logs_dir: str
    brainfile_path: str


TaskLookup = dict[str, Any]


def get_dirs(brainfile_path: str) -> WorkspaceDirs:
    resolved = Path(brainfile_path).resolve()
    dot_dir = resolved.parent
    return WorkspaceDirs(
        dot_dir=str(dot_dir),
        board_dir=str(dot_dir / "board"),
        logs_dir=str(dot_dir / "logs"),
        brainfile_path=str(resolved),
    )


def is_workspace(brainfile_path: str) -> bool:
    dirs = get_dirs(brainfile_path)
    return Path(dirs.board_dir).exists()


def ensure_dirs(brainfile_path: str) -> WorkspaceDirs:
    dirs = get_dirs(brainfile_path)
    Path(dirs.board_dir).mkdir(parents=True, exist_ok=True)
    Path(dirs.logs_dir).mkdir(parents=True, exist_ok=True)
    return dirs


def get_task_file_path(board_dir: str, task_id: str) -> str:
    return str(Path(board_dir) / task_file_name(task_id))


def get_log_file_path(logs_dir: str, task_id: str) -> str:
    return str(Path(logs_dir) / task_file_name(task_id))


def _match_task_document(file_path: str, task_id: str, is_log: bool) -> TaskLookup | None:
    task_doc = read_task_file(file_path)
    if task_doc and task_doc.task.id == task_id:
        return {"doc": task_doc, "file_path": file_path, "is_log": is_log}
    return None


def _scan_task_documents(
    dir_path: str,
    task_id: str,
    is_log: bool,
    fallback_path: str,
) -> TaskLookup | None:
    for doc in read_tasks_dir(dir_path):
        if doc.task.id == task_id:
            return {
                "doc": doc,
                "file_path": doc.file_path or fallback_path,
                "is_log": is_log,
            }
    return None


def _find_task_in_directory(
    dir_path: str,
    fallback_path: str,
    task_id: str,
    is_log: bool,
) -> TaskLookup | None:
    return _match_task_document(fallback_path, task_id, is_log) or _scan_task_documents(
        dir_path,
        task_id,
        is_log,
        fallback_path,
    )


def find_task(
    dirs: WorkspaceDirs,
    task_id: str,
    search_logs: bool = False,
) -> TaskLookup | None:
    """Find a task across active tasks and optionally logs.

    Returns a dict: {doc, file_path, is_log} or None.
    """

    task_path = get_task_file_path(dirs.board_dir, task_id)
    found = _find_task_in_directory(dirs.board_dir, task_path, task_id, False)
    if found is not None:
        return found

    if not search_logs:
        return None

    log_path = get_log_file_path(dirs.logs_dir, task_id)
    return _find_task_in_directory(dirs.logs_dir, log_path, task_id, True)


_DESCRIPTION_RE = re.compile(r"## Description\n([\s\S]*?)(?=\n## |\n*$)")
_LOG_RE = re.compile(r"## Log\n([\s\S]*?)(?=\n## |\n*$)")


def extract_description(body: str) -> str | None:
    match = _DESCRIPTION_RE.search(body)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def extract_log(body: str) -> str | None:
    match = _LOG_RE.search(body)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def compose_body(description: str | None = None, log: str | None = None) -> str:
    sections: list[str] = []

    if description and description.strip():
        sections.append(f"## Description\n{description.strip()}")

    if log and log.strip():
        sections.append(f"## Log\n{log.strip()}")

    if not sections:
        return ""

    return "\n\n".join(sections) + "\n"


def read_board_config(brainfile_path: str) -> BoardConfig:
    content = Path(brainfile_path).read_text(encoding="utf-8")

    data = BrainfileParser.parse(content)
    if not data:
        raise ValueError(f"Failed to parse brainfile: {brainfile_path}")

    return BoardConfig.model_validate(data)


def _load_board_config_mapping(yaml_content: str) -> dict[str, Any]:
    yaml = create_yaml()
    try:
        parsed: Any = yaml.load(StringIO(yaml_content))
    except Exception as exc:
        raise ValueError(f"Failed to parse YAML frontmatter: {exc}") from exc

    if not parsed or not isinstance(parsed, dict):
        raise ValueError("YAML frontmatter is empty or not a mapping")

    return parsed


def parse_board_config(content: str) -> tuple[BoardConfig, str]:
    """Parse raw board config file content into a (BoardConfig, body) tuple.

    The content must be a markdown string with YAML frontmatter delimited by ``---``.
    Returns the parsed config and the body text after the frontmatter.

    Raises :class:`ValueError` for invalid inputs.
    """

    sections = extract_frontmatter_sections(content)
    if sections is None:
        if has_frontmatter_start(content):
            raise ValueError("Missing closing YAML frontmatter delimiter")
        raise ValueError("Content does not start with YAML frontmatter delimiter")

    yaml_content, body_content = sections
    parsed = _load_board_config_mapping(yaml_content)
    config = BoardConfig.model_validate(parsed)
    return config, trim_leading_blank_line(body_content)


def serialize_board_config(config: BoardConfig, body: str = "") -> str:
    """Serialize a BoardConfig and body into a markdown string with YAML frontmatter."""

    config_dict = config.model_dump(by_alias=True, exclude_none=True)

    yaml = create_yaml()
    buf = StringIO()
    yaml.dump(config_dict, buf)
    yaml_str = buf.getvalue()
    if yaml_str and not yaml_str.endswith("\n"):
        yaml_str += "\n"

    parts: list[str] = ["---\n", yaml_str, "---\n"]

    if body:
        parts.extend(["\n", body])
        if not body.endswith("\n"):
            parts.append("\n")

    return "".join(parts)


def write_board_config(file_path: str, config: BoardConfig, body: str = "") -> None:
    """Write a board config to disk as a markdown file with YAML frontmatter."""

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_board_config(config, body), encoding="utf-8")
