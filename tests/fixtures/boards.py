"""Test board fixtures - ported from TypeScript test-boards.ts."""

from brainfile import (
    AgentInstructions,
    Board,
    Column,
    Priority,
    Rule,
    Rules,
    StatsConfig,
    Subtask,
    Task,
    TemplateType,
)

# Minimal board with one empty column
MINIMAL_BOARD = Board(
    title="Test Board",
    columns=[
        Column(
            id="todo",
            title="To Do",
            tasks=[],
        ),
    ],
)

MINIMAL_BOARD_DICT = {
    "title": "Test Board",
    "columns": [
        {
            "id": "todo",
            "title": "To Do",
            "tasks": [],
        },
    ],
}

MINIMAL_BOARD_MARKDOWN = """---
title: Test Board
columns:
  - id: todo
    title: To Do
    tasks: []
---
"""

# Complex board with all features
COMPLEX_BOARD = Board(
    title="Complex Board",
    protocol_version="1.0",
    agent=AgentInstructions(
        instructions=["Test instruction"],
    ),
    rules=Rules(
        always=[Rule(id=1, rule="Always test")],
        never=[Rule(id=1, rule="Never skip tests")],
        prefer=[Rule(id=1, rule="Prefer simple solutions")],
        context=[Rule(id=1, rule="Context matters")],
    ),
    stats_config=StatsConfig(
        columns=["todo", "done"],
    ),
    columns=[
        Column(
            id="todo",
            title="To Do",
            tasks=[
                Task(
                    id="task-1",
                    title="Complete Task",
                    description="Full description",
                    assignee="alice",
                    tags=["bug", "urgent"],
                    priority=Priority.HIGH,
                    template=TemplateType.BUG,
                    related_files=["src/app.ts"],
                    subtasks=[
                        Subtask(id="sub-1", title="Step 1", completed=True),
                        Subtask(id="sub-2", title="Step 2", completed=False),
                    ],
                ),
            ],
        ),
        Column(
            id="done",
            title="Done",
            tasks=[],
        ),
    ],
    archive=[
        Task(
            id="archived-1",
            title="Old Task",
        ),
    ],
)

COMPLEX_BOARD_DICT = {
    "title": "Complex Board",
    "protocolVersion": "1.0",
    "agent": {
        "instructions": ["Test instruction"],
    },
    "rules": {
        "always": [{"id": 1, "rule": "Always test"}],
        "never": [{"id": 1, "rule": "Never skip tests"}],
        "prefer": [{"id": 1, "rule": "Prefer simple solutions"}],
        "context": [{"id": 1, "rule": "Context matters"}],
    },
    "statsConfig": {
        "columns": ["todo", "done"],
    },
    "columns": [
        {
            "id": "todo",
            "title": "To Do",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "Complete Task",
                    "description": "Full description",
                    "assignee": "alice",
                    "tags": ["bug", "urgent"],
                    "priority": "high",
                    "template": "bug",
                    "relatedFiles": ["src/app.ts"],
                    "subtasks": [
                        {"id": "sub-1", "title": "Step 1", "completed": True},
                        {"id": "sub-2", "title": "Step 2", "completed": False},
                    ],
                },
            ],
        },
        {
            "id": "done",
            "title": "Done",
            "tasks": [],
        },
    ],
    "archive": [
        {
            "id": "archived-1",
            "title": "Old Task",
        },
    ],
}

# Invalid board configurations for testing validation
INVALID_BOARDS = {
    "no_title": {"columns": []},
    "no_columns": {"title": "Test"},
    "invalid_priority": {
        "title": "Test",
        "columns": [
            {
                "id": "todo",
                "title": "To Do",
                "tasks": [
                    {
                        "id": "task-1",
                        "title": "Task",
                        "priority": "super-high",
                    },
                ],
            },
        ],
    },
    "invalid_template": {
        "title": "Test",
        "columns": [
            {
                "id": "todo",
                "title": "To Do",
                "tasks": [
                    {
                        "id": "task-1",
                        "title": "Task",
                        "template": "unknown",
                    },
                ],
            },
        ],
    },
}
