"""brainfile.task_file

V2 per-task file reader/writer.

Parity notes (matches TypeScript core v2 `taskFile.ts`):

* Task files are markdown documents with YAML frontmatter delimited by `---`.
* ``parse_task_content`` returns ``None`` (not an exception) for invalid input.
* Parsed body trims a single leading blank line (convention: one blank line after
  frontmatter), but is otherwise preserved.
* Serialization ensures a blank line between frontmatter and body (when body is
  non-empty) and ensures a trailing newline.
* ``read_task_file`` populates an absolute ``file_path``.
"""

from __future__ import annotations

from pathlib import Path
from io import StringIO
from typing import Any, overload

from ._yaml import create_yaml
from .frontmatter import extract_frontmatter_sections, trim_leading_blank_line
from .models import Task, TaskDocument

__all__ = [
    "task_file_name",
    "parse_task_content",
    "serialize_task_content",
    "read_task_file",
    "write_task_file",
    "read_tasks_dir",
]


def task_file_name(task_id: str) -> str:
    """Return the conventional filename for a task id (e.g. ``task-1.md``)."""

    return f"{task_id}.md"


def _load_task_mapping(yaml_content: str) -> dict[str, Any] | None:
    yaml = create_yaml()
    try:
        parsed: Any = yaml.load(StringIO(yaml_content))
    except Exception:
        return None

    if not parsed or not isinstance(parsed, dict):
        return None

    if not parsed.get("id") or not parsed.get("title"):
        return None

    return parsed


def parse_task_content(content: str) -> TaskDocument | None:
    """Parse raw task file content into a :class:`~brainfile.models.TaskDocument`.

    Returns ``None`` for invalid inputs.
    """

    sections = extract_frontmatter_sections(content)
    if sections is None:
        return None

    yaml_content, body_content = sections
    parsed = _load_task_mapping(yaml_content)
    if parsed is None:
        return None

    task = Task.model_validate(parsed)
    return TaskDocument(task=task, body=trim_leading_blank_line(body_content))


def serialize_task_content(task: Task, body: str = "") -> str:
    """Serialize a task and body into v2 markdown file content."""

    task_dict = task.model_dump(exclude_none=True, by_alias=True)

    yaml = create_yaml()
    buf = StringIO()
    yaml.dump(task_dict, buf)
    yaml_str = buf.getvalue()
    if yaml_str and not yaml_str.endswith("\n"):
        yaml_str += "\n"

    parts: list[str] = ["---\n", yaml_str, "---\n"]

    if body:
        # Ensure a blank line between frontmatter and body
        parts.append("\n")
        parts.append(body)
        # Ensure trailing newline
        if not body.endswith("\n"):
            parts.append("\n")

    return "".join(parts)


def read_task_file(file_path: str) -> TaskDocument | None:
    """Read and parse a task file from disk.

    Returns None when the file does not exist or is invalid.
    """

    path = Path(file_path)
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    doc = parse_task_content(content)
    if not doc:
        return None

    doc.file_path = str(path.resolve())
    return doc


@overload
def write_task_file(file_path: str, doc: TaskDocument) -> None: ...


@overload
def write_task_file(file_path: str, task: Task, body: str = "") -> None: ...


def write_task_file(file_path: str, task_or_doc: TaskDocument | Task, body: str = "") -> None:
    """Write a task file to disk.

    This is intentionally compatible with both:

    * legacy Python usage: ``write_task_file(path, TaskDocument(...))``
    * TS parity usage: ``write_task_file(path, task, body)``
    """

    if isinstance(task_or_doc, TaskDocument):
        task = task_or_doc.task
        actual_body = task_or_doc.body or ""
        if body:
            actual_body = body
    else:
        task = task_or_doc
        actual_body = body

    path = Path(file_path)
    if path.parent != Path():
        path.parent.mkdir(parents=True, exist_ok=True)

    content = serialize_task_content(task, actual_body)
    path.write_text(content, encoding="utf-8")


def read_tasks_dir(dir_path: str) -> list[TaskDocument]:
    """Read all task files from a directory."""

    try:
        entries = Path(dir_path).iterdir()
    except OSError:
        return []

    docs: list[TaskDocument] = []

    for entry in entries:
        if entry.suffix != ".md" or not entry.is_file():
            continue
        doc = read_task_file(str(entry))
        if doc:
            docs.append(doc)

    return docs
