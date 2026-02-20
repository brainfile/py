"""brainfile.task_file

V2 per-task file reader/writer.

Parity notes (matches TypeScript core v2 `taskFile.ts`):

* Task files are markdown documents with YAML frontmatter delimited by `---`.
* ``parseTaskContent`` returns ``None`` (not an exception) for invalid input.
* Parsed body trims a single leading blank line (convention: one blank line after
  frontmatter), but is otherwise preserved.
* Serialization ensures a blank line between frontmatter and body (when body is
  non-empty) and ensures a trailing newline.
* ``readTaskFile`` populates an absolute ``file_path``.

The functions are intentionally exported in camelCase to align with TS core
exports.
"""

from __future__ import annotations

# ruff: noqa: N802,N803
import contextlib
import os
from io import StringIO
from typing import Any, overload

from ruamel.yaml import YAML

from .models import Task, TaskDocument


def taskFileName(taskId: str) -> str:
    """Return the conventional filename for a task id (e.g. ``task-1.md``)."""

    return f"{taskId}.md"


def _create_yaml() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    # Match TS `sortKeys: false` behavior as closely as ruamel allows.
    with contextlib.suppress(Exception):
        yaml.sort_base_mapping_type_on_output = False  # type: ignore[attr-defined]
    return yaml


def parseTaskContent(content: str) -> TaskDocument | None:
    """Parse raw task file content into a :class:`~brainfile.models.TaskDocument`.

    Returns ``None`` for invalid inputs.
    """

    lines = content.split("\n")

    # Must start with frontmatter delimiter
    if not lines or lines[0].strip() != "---":
        return None

    # Find closing delimiter
    end_index = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_index = i
            break

    if end_index == -1:
        return None

    yaml_content = "\n".join(lines[1:end_index])
    body_content = "\n".join(lines[end_index + 1 :])

    yaml = _create_yaml()
    try:
        parsed: Any = yaml.load(StringIO(yaml_content))
    except Exception:
        return None

    if not parsed or not isinstance(parsed, dict):
        return None

    # Required fields
    if not parsed.get("id") or not parsed.get("title"):
        return None

    try:
        task = Task.model_validate(parsed)
    except Exception:
        return None

    # Trim a single leading blank line after frontmatter (if present)
    body = body_content[1:] if body_content.startswith("\n") else body_content

    return TaskDocument(task=task, body=body)


def serializeTaskContent(task: Task, body: str = "") -> str:
    """Serialize a task and body into v2 markdown file content."""

    task_dict = task.model_dump(exclude_none=True, by_alias=True)

    yaml = _create_yaml()
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


def readTaskFile(filePath: str) -> TaskDocument | None:
    """Read and parse a task file from disk.

    Returns None when the file does not exist or is invalid.
    """

    try:
        with open(filePath, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    doc = parseTaskContent(content)
    if not doc:
        return None

    doc.file_path = os.path.abspath(filePath)
    return doc


@overload
def writeTaskFile(filePath: str, doc: TaskDocument) -> None: ...


@overload
def writeTaskFile(filePath: str, task: Task, body: str = "") -> None: ...


def writeTaskFile(filePath: str, task_or_doc: TaskDocument | Task, body: str = "") -> None:
    """Write a task file to disk.

    This is intentionally compatible with both:

    * legacy Python usage: ``writeTaskFile(path, TaskDocument(...))``
    * TS parity usage: ``writeTaskFile(path, task, body)``
    """

    if isinstance(task_or_doc, TaskDocument):
        task = task_or_doc.task
        actual_body = task_or_doc.body or ""
        if body:
            actual_body = body
    else:
        task = task_or_doc
        actual_body = body

    parent_dir = os.path.dirname(filePath)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    content = serializeTaskContent(task, actual_body)
    with open(filePath, "w", encoding="utf-8") as f:
        f.write(content)


def readTasksDir(dirPath: str) -> list[TaskDocument]:
    """Read all task files from a directory."""

    try:
        entries = os.listdir(dirPath)
    except Exception:
        return []

    docs: list[TaskDocument] = []

    for name in entries:
        if not name.endswith(".md"):
            continue
        file_path = os.path.join(dirPath, name)
        if not os.path.isfile(file_path):
            continue
        doc = readTaskFile(file_path)
        if doc:
            docs.append(doc)

    return docs
