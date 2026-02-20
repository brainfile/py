"""brainfile.formatters

Formatters for external service payloads (GitHub, Linear).

Pure transformation functions that convert Brainfile tasks into
payloads suitable for GitHub Issues, Linear, and other services.

This mirrors TS core v2 ``formatters.ts``.
"""

from __future__ import annotations

# ruff: noqa: N802,N803,N815
from typing import Literal, TypedDict

from .models import Subtask, Task


class GitHubIssuePayload(TypedDict, total=False):
    """Payload for creating a GitHub Issue."""

    title: str
    body: str
    labels: list[str] | None
    state: Literal["open", "closed"]


class GitHubFormatOptions(TypedDict, total=False):
    """Options for formatting a task for GitHub."""

    includeMeta: bool
    includeSubtasks: bool
    includeRelatedFiles: bool
    resolvedBy: str
    resolvedByPR: str
    fromColumn: str
    boardTitle: str
    extraLabels: list[str]
    includeTaskId: bool


class LinearIssuePayload(TypedDict, total=False):
    """Payload for creating a Linear Issue."""

    title: str
    description: str
    priority: int | None
    labelNames: list[str] | None
    stateName: str


class LinearFormatOptions(TypedDict, total=False):
    """Options for formatting a task for Linear."""

    includeMeta: bool
    includeSubtasks: bool
    includeRelatedFiles: bool
    resolvedBy: str
    resolvedByPR: str
    fromColumn: str
    boardTitle: str
    stateName: str
    includeTaskId: bool


def _format_subtasks_markdown(subtasks: list[Subtask]) -> str:
    """Format subtasks as a markdown checklist."""
    items = [f"- [{'x' if st.completed else ' '}] {st.title}" for st in subtasks]
    return "## Subtasks\n\n" + "\n".join(items)


def _format_metadata_section(
    task: Task, context: dict[str, str | None]
) -> str | None:
    """Format task metadata as a markdown section."""
    lines: list[str] = []

    if context.get("boardTitle"):
        lines.append(f"**Board:** {context['boardTitle']}")

    if context.get("fromColumn"):
        lines.append(f"**Column:** {context['fromColumn']}")

    if task.priority:
        lines.append(f"**Priority:** {task.priority.value if hasattr(task.priority, 'value') else task.priority}")

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
    resolvedBy: str | None = None, resolvedByPR: str | None = None
) -> str:
    """Format resolution information."""
    lines: list[str] = ["## Resolution"]

    if resolvedByPR:
        lines.append(f"\n**Pull Request:** {resolvedByPR}")

    if resolvedBy:
        lines.append(f"\n**Commit:** {resolvedBy}")

    return "".join(lines)


def formatTaskForGitHub(
    task: Task, options: GitHubFormatOptions | None = None
) -> GitHubIssuePayload:
    """Format a Brainfile task as a GitHub Issue payload."""
    options = options or {}
    include_meta = options.get("includeMeta", True)
    include_subtasks = options.get("includeSubtasks", True)
    include_related_files = options.get("includeRelatedFiles", True)
    resolved_by = options.get("resolvedBy")
    resolved_by_pr = options.get("resolvedByPR")
    from_column = options.get("fromColumn")
    board_title = options.get("boardTitle")
    extra_labels = options.get("extraLabels", [])
    include_task_id = options.get("includeTaskId", True)

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
            task, {"fromColumn": from_column, "boardTitle": board_title}
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


def formatTaskForLinear(
    task: Task, options: LinearFormatOptions | None = None
) -> LinearIssuePayload:
    """Format a Brainfile task as a Linear Issue payload."""
    options = options or {}
    include_meta = options.get("includeMeta", True)
    include_subtasks = options.get("includeSubtasks", True)
    include_related_files = options.get("includeRelatedFiles", True)
    resolved_by = options.get("resolvedBy")
    resolved_by_pr = options.get("resolvedByPR")
    from_column = options.get("fromColumn")
    board_title = options.get("boardTitle")
    state_name = options.get("stateName", "Done")
    include_task_id = options.get("includeTaskId", False)

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
            task, {"fromColumn": from_column, "boardTitle": board_title}
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

    p_val = task.priority.value if task.priority and hasattr(task.priority, "value") else task.priority
    
    return {
        "title": title,
        "description": "\n\n".join(sections),
        "priority": _map_priority_to_linear(p_val),
        "labelNames": list(task.tags) if task.tags else None,
        "stateName": state_name,
    }
