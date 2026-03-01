"""brainfile.formatters

Formatters for external service payloads (GitHub, Linear).

Pure transformation functions that convert Brainfile tasks into
payloads suitable for GitHub Issues, Linear, and other services.

This mirrors TS core v2 ``formatters.ts``.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from .models import Subtask, Task


class GitHubIssuePayload(TypedDict, total=False):  # noqa: N815
    """Payload for creating a GitHub Issue."""

    title: str
    body: str
    labels: list[str] | None
    state: Literal["open", "closed"]


class GitHubFormatOptions(TypedDict, total=False):
    """Options for formatting a task for GitHub."""

    include_meta: bool
    include_subtasks: bool
    include_related_files: bool
    resolved_by: str
    resolved_by_pr: str
    from_column: str
    board_title: str
    extra_labels: list[str]
    include_task_id: bool


class LinearIssuePayload(TypedDict, total=False):  # noqa: N815
    """Payload for creating a Linear Issue."""

    title: str
    description: str
    priority: int | None
    labelNames: list[str] | None  # noqa: N815
    stateName: str  # noqa: N815


class LinearFormatOptions(TypedDict, total=False):
    """Options for formatting a task for Linear."""

    include_meta: bool
    include_subtasks: bool
    include_related_files: bool
    resolved_by: str
    resolved_by_pr: str
    from_column: str
    board_title: str
    state_name: str
    include_task_id: bool


def _format_subtasks_markdown(subtasks: list[Subtask]) -> str:
    """Format subtasks as a markdown checklist."""
    items = [f"- [{'x' if st.completed else ' '}] {st.title}" for st in subtasks]
    return "## Subtasks\n\n" + "\n".join(items)


def _format_metadata_section(
    task: Task, context: dict[str, str | None]
) -> str | None:
    """Format task metadata as a markdown section."""
    lines: list[str] = []

    if context.get("board_title"):
        lines.append(f"**Board:** {context['board_title']}")

    if context.get("from_column"):
        lines.append(f"**Column:** {context['from_column']}")

    if task.priority:
        p_val = task.priority.value if hasattr(task.priority, "value") else task.priority
        lines.append(f"**Priority:** {p_val}")

    if task.assignee:
        lines.append(f"**Assignee:** {task.assignee}")

    if task.due_date:
        lines.append(f"**Due Date:** {task.due_date}")

    if task.created_at:
        lines.append(f"**Created:** {task.created_at}")

    if not lines:
        return None

    return "## Details\n\n" + "\n".join(lines)


def _format_related_files_section(files: list[str]) -> str:
    """Format related files as a markdown section."""
    items = [f"- `{f}`" for f in files]
    return "## Related Files\n\n" + "\n".join(items)


def _format_resolution_section(
    resolved_by: str | None = None, resolved_by_pr: str | None = None
) -> str:
    """Format resolution information."""
    lines: list[str] = ["## Resolution"]

    if resolved_by_pr:
        lines.append(f"\n**Pull Request:** {resolved_by_pr}")

    if resolved_by:
        lines.append(f"\n**Commit:** {resolved_by}")

    return "".join(lines)


def format_task_for_github(
    task: Task, options: GitHubFormatOptions | None = None
) -> GitHubIssuePayload:
    """Format a Brainfile task as a GitHub Issue payload."""
    options = options or {}
    include_meta = options.get("include_meta", True)
    include_subtasks = options.get("include_subtasks", True)
    include_related_files = options.get("include_related_files", True)
    resolved_by = options.get("resolved_by")
    resolved_by_pr = options.get("resolved_by_pr")
    from_column = options.get("from_column")
    board_title = options.get("board_title")
    extra_labels = options.get("extra_labels", [])
    include_task_id = options.get("include_task_id", True)

    # Build title
    title = f"[{task.id}] {task.title}" if include_task_id else task.title

    # Build body sections
    sections: list[str] = []

    # Description
    if task.description:
        sections.append(task.description)

    # Subtasks as checklist
    if include_subtasks and task.subtasks:
        sections.append(_format_subtasks_markdown(task.subtasks))

    # Metadata section
    if include_meta:
        meta = _format_metadata_section(
            task, {"from_column": from_column, "board_title": board_title}
        )
        if meta:
            sections.append(meta)

    # Related files
    if include_related_files and task.related_files:
        sections.append(_format_related_files_section(task.related_files))

    # Resolution info
    if resolved_by or resolved_by_pr:
        sections.append(_format_resolution_section(resolved_by, resolved_by_pr))

    # Footer
    sections.append("---\n*Archived from brainfile.md*")

    # Build labels from tags + extras
    labels: list[str] = list(task.tags or []) + extra_labels

    # Add priority as label if present
    if task.priority:
        p_val = task.priority.value if hasattr(task.priority, "value") else task.priority
        labels.append(f"priority:{p_val}")

    # Add template type as label if present
    if task.template:
        t_val = task.template.value if hasattr(task.template, "value") else task.template
        labels.append(str(t_val))

    return {
        "title": title,
        "body": "\n\n".join(sections),
        "labels": labels if labels else None,
        "state": "closed",
    }


def _map_priority_to_linear(priority: str | None) -> int | None:
    """Map Brainfile priority to Linear priority number."""
    if not priority:
        return None

    p = priority.lower()
    if p == "critical":
        return 1
    if p == "high":
        return 2
    if p == "medium":
        return 3
    if p == "low":
        return 4
    return 0


def format_task_for_linear(
    task: Task, options: LinearFormatOptions | None = None
) -> LinearIssuePayload:
    """Format a Brainfile task as a Linear Issue payload."""
    options = options or {}
    include_meta = options.get("include_meta", True)
    include_subtasks = options.get("include_subtasks", True)
    include_related_files = options.get("include_related_files", True)
    resolved_by = options.get("resolved_by")
    resolved_by_pr = options.get("resolved_by_pr")
    from_column = options.get("from_column")
    board_title = options.get("board_title")
    state_name = options.get("state_name", "Done")
    include_task_id = options.get("include_task_id", False)

    # Build title
    title = f"[{task.id}] {task.title}" if include_task_id else task.title

    # Build description sections
    sections: list[str] = []

    # Description
    if task.description:
        sections.append(task.description)

    # Subtasks as checklist
    if include_subtasks and task.subtasks:
        sections.append(_format_subtasks_markdown(task.subtasks))

    # Metadata section
    if include_meta:
        meta = _format_metadata_section(
            task, {"from_column": from_column, "board_title": board_title}
        )
        if meta:
            sections.append(meta)

    # Related files
    if include_related_files and task.related_files:
        sections.append(_format_related_files_section(task.related_files))

    # Resolution info
    if resolved_by or resolved_by_pr:
        sections.append(_format_resolution_section(resolved_by, resolved_by_pr))

    # Footer
    sections.append("---\n*Archived from brainfile.md*")

    p_val = (
        task.priority.value
        if task.priority and hasattr(task.priority, "value")
        else task.priority
    )

    return {
        "title": title,
        "description": "\n\n".join(sections),
        "priority": _map_priority_to_linear(p_val),
        "labelNames": list(task.tags) if task.tags else None,
        "stateName": state_name,
    }
