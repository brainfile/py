"""Shared pytest fixtures for brainfile tests."""

import pytest

from brainfile import Board, Column, Priority, Subtask, Task

from .fixtures.boards import (
    COMPLEX_BOARD,
    COMPLEX_BOARD_DICT,
    MINIMAL_BOARD,
    MINIMAL_BOARD_DICT,
    MINIMAL_BOARD_MARKDOWN,
)


@pytest.fixture
def minimal_board() -> Board:
    """Return a minimal board with one empty column."""
    return MINIMAL_BOARD.model_copy(deep=True)


@pytest.fixture
def minimal_board_dict() -> dict:
    """Return a minimal board as a dict."""
    return MINIMAL_BOARD_DICT.copy()


@pytest.fixture
def minimal_board_markdown() -> str:
    """Return minimal board as markdown."""
    return MINIMAL_BOARD_MARKDOWN


@pytest.fixture
def complex_board() -> Board:
    """Return a complex board with all features."""
    return COMPLEX_BOARD.model_copy(deep=True)


@pytest.fixture
def complex_board_dict() -> dict:
    """Return a complex board as a dict."""
    import copy
    return copy.deepcopy(COMPLEX_BOARD_DICT)


@pytest.fixture
def board_with_tasks() -> Board:
    """Return a board with multiple tasks for testing operations."""
    return Board(
        title="Test Board",
        columns=[
            Column(
                id="todo",
                title="To Do",
                tasks=[
                    Task(
                        id="task-1",
                        title="First Task",
                        description="Description 1",
                        priority=Priority.HIGH,
                        tags=["urgent"],
                    ),
                    Task(
                        id="task-2",
                        title="Second Task",
                        description="Description 2",
                        priority=Priority.MEDIUM,
                    ),
                ],
            ),
            Column(
                id="in-progress",
                title="In Progress",
                tasks=[
                    Task(
                        id="task-3",
                        title="Third Task",
                        assignee="alice",
                    ),
                ],
            ),
            Column(
                id="done",
                title="Done",
                tasks=[],
            ),
        ],
    )


@pytest.fixture
def board_with_subtasks() -> Board:
    """Return a board with tasks that have subtasks."""
    return Board(
        title="Subtask Test Board",
        columns=[
            Column(
                id="todo",
                title="To Do",
                tasks=[
                    Task(
                        id="task-1",
                        title="Task with subtasks",
                        subtasks=[
                            Subtask(id="task-1-1", title="Subtask 1", completed=False),
                            Subtask(id="task-1-2", title="Subtask 2", completed=True),
                            Subtask(id="task-1-3", title="Subtask 3", completed=False),
                        ],
                    ),
                ],
            ),
        ],
    )


@pytest.fixture
def sample_markdown_content() -> str:
    """Return sample brainfile markdown content."""
    return """---
title: Sample Board
columns:
  - id: todo
    title: To Do
    tasks:
      - id: task-1
        title: Sample Task
        description: A sample task description
        priority: high
        tags:
          - sample
          - test
---
"""


@pytest.fixture
def invalid_yaml_content() -> str:
    """Return invalid YAML content for testing error handling."""
    return """---
title: Invalid Board
columns:
  - id: todo
    title: To Do
    tasks:
      - id: task-1
        title: Bad: Unquoted: Colons
---
"""
