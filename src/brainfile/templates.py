"""
Task template system for creating structured tasks from predefined templates.

This module provides built-in templates for common task types (bug reports,
feature requests, refactoring tasks) and utilities for processing templates.
"""

from __future__ import annotations

import re
import time
import random
import string
from typing import Any

from .models import Priority, Subtask, Task, TaskTemplate, TemplateType, TemplateVariable


# Built-in task templates
BUILT_IN_TEMPLATES: list[TaskTemplate] = [
    TaskTemplate(
        id="bug-report",
        name="Bug Report",
        description="Template for reporting bugs and issues",
        is_built_in=True,
        template=Task(
            id="",  # Will be generated
            title="{title}",
            description=(
                "## Bug Description\n{description}\n\n"
                "## Steps to Reproduce\n1. \n2. \n3. \n\n"
                "## Expected Behavior\n\n"
                "## Actual Behavior\n\n"
                "## Environment\n- OS: \n- Version: "
            ),
            template=TemplateType.BUG,
            priority=Priority.HIGH,
            tags=["bug", "needs-triage"],
            subtasks=[
                Subtask(id="bug-1", title="Reproduce the issue", completed=False),
                Subtask(id="bug-2", title="Identify root cause", completed=False),
                Subtask(id="bug-3", title="Implement fix", completed=False),
                Subtask(id="bug-4", title="Write tests", completed=False),
                Subtask(id="bug-5", title="Verify fix in production", completed=False),
            ],
        ),
        variables=[
            TemplateVariable(
                name="title",
                description="Brief bug title",
                required=True,
            ),
            TemplateVariable(
                name="description",
                description="Detailed bug description",
                required=True,
            ),
        ],
    ),
    TaskTemplate(
        id="feature-request",
        name="Feature Request",
        description="Template for proposing new features",
        is_built_in=True,
        template=Task(
            id="",  # Will be generated
            title="{title}",
            description=(
                "## Feature Description\n{description}\n\n"
                "## Use Cases\n- \n- \n\n"
                "## Proposed Implementation\n\n"
                "## Acceptance Criteria\n- [ ] \n- [ ] "
            ),
            template=TemplateType.FEATURE,
            priority=Priority.MEDIUM,
            tags=["feature", "enhancement"],
            subtasks=[
                Subtask(id="feature-1", title="Design specification", completed=False),
                Subtask(id="feature-2", title="Implement core functionality", completed=False),
                Subtask(id="feature-3", title="Add unit tests", completed=False),
                Subtask(id="feature-4", title="Add integration tests", completed=False),
                Subtask(id="feature-5", title="Update documentation", completed=False),
                Subtask(id="feature-6", title="Code review", completed=False),
            ],
        ),
        variables=[
            TemplateVariable(
                name="title",
                description="Feature title",
                required=True,
            ),
            TemplateVariable(
                name="description",
                description="Feature description and rationale",
                required=True,
            ),
        ],
    ),
    TaskTemplate(
        id="refactor",
        name="Code Refactor",
        description="Template for code refactoring tasks",
        is_built_in=True,
        template=Task(
            id="",  # Will be generated
            title="Refactor: {area}",
            description=(
                "## Refactoring Scope\n{description}\n\n"
                "## Motivation\n- \n\n"
                "## Changes\n- [ ] \n- [ ] \n\n"
                "## Testing Plan\n"
            ),
            template=TemplateType.REFACTOR,
            priority=Priority.LOW,
            tags=["refactor", "technical-debt"],
            subtasks=[
                Subtask(id="refactor-1", title="Analyze current implementation", completed=False),
                Subtask(id="refactor-2", title="Design new structure", completed=False),
                Subtask(id="refactor-3", title="Implement refactoring", completed=False),
                Subtask(id="refactor-4", title="Update/add tests", completed=False),
                Subtask(id="refactor-5", title="Update documentation", completed=False),
                Subtask(id="refactor-6", title="Performance testing", completed=False),
            ],
        ),
        variables=[
            TemplateVariable(
                name="area",
                description="Area or component to refactor",
                required=True,
            ),
            TemplateVariable(
                name="description",
                description="Details about what needs refactoring",
                required=True,
            ),
        ],
    ),
]


def generate_task_id() -> str:
    """
    Generate a unique task ID.

    Returns:
        A unique task ID string
    """
    timestamp = int(time.time() * 1000)
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=9))
    return f"task-{timestamp}-{random_suffix}"


def generate_subtask_id(parent_id: str, index: int) -> str:
    """
    Generate a subtask ID based on parent task ID.

    Args:
        parent_id: The parent task ID
        index: The index of the subtask (0-based)

    Returns:
        A subtask ID string
    """
    return f"{parent_id}-{index + 1}"


def _substitute_variables(text: str, values: dict[str, str]) -> str:
    """
    Substitute variables in a template string.

    Args:
        text: The text containing variable placeholders
        values: Variable values to substitute

    Returns:
        Text with substituted values
    """

    def replace_var(match: re.Match[str]) -> str:
        variable = match.group(1)
        return values.get(variable, match.group(0))

    return re.sub(r"\{(\w+)\}", replace_var, text)


def process_template(
    template: TaskTemplate,
    values: dict[str, str],
) -> dict[str, Any]:
    """
    Process a template and substitute variable values.

    Args:
        template: The template to process
        values: Variable values to substitute

    Returns:
        A partial Task object with substituted values as a dict
    """
    # Deep copy the template task
    processed_task = template.template.model_dump(by_alias=True, exclude_none=True)

    # Process title
    if "title" in processed_task:
        processed_task["title"] = _substitute_variables(processed_task["title"], values)

    # Process description
    if "description" in processed_task:
        processed_task["description"] = _substitute_variables(
            processed_task["description"], values
        )

    # Generate new IDs for subtasks to avoid duplicates
    if "subtasks" in processed_task and processed_task["subtasks"]:
        new_task_id = generate_task_id()
        processed_task["subtasks"] = [
            {
                **subtask,
                "id": generate_subtask_id(new_task_id, index),
            }
            for index, subtask in enumerate(processed_task["subtasks"])
        ]

    return processed_task


def get_template_by_id(template_id: str) -> TaskTemplate | None:
    """
    Get a template by ID.

    Args:
        template_id: The template ID

    Returns:
        The template or None if not found
    """
    for template in BUILT_IN_TEMPLATES:
        if template.id == template_id:
            return template
    return None


def get_all_template_ids() -> list[str]:
    """
    Get all template IDs.

    Returns:
        Array of template IDs
    """
    return [template.id for template in BUILT_IN_TEMPLATES]
