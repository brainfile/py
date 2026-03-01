"""Test fixtures — board config dicts for parser/inference tests."""

MINIMAL_BOARD_DICT = {
    "title": "Test Board",
    "columns": [
        {
            "id": "todo",
            "title": "To Do",
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
        },
        {
            "id": "done",
            "title": "Done",
        },
    ],
}
