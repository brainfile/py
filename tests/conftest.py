"""Shared pytest fixtures for brainfile tests."""

import pytest

from brainfile import Priority, Subtask, Task


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
def minimal_board_markdown() -> str:
    """Return minimal board config markdown."""
    return """---
title: Test Board
columns:
  - id: todo
    title: To Do
    tasks: []
---
"""
