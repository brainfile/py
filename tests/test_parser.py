"""Tests for the parser module."""

import pytest

from brainfile import BrainfileParser, BrainfileType, RendererType


class TestBrainfileParser:
    """Tests for BrainfileParser."""

    def test_parse_minimal_board(self, minimal_board_markdown: str):
        """Test parsing a minimal board."""
        result = BrainfileParser.parse(minimal_board_markdown)
        assert result is not None
        assert result["title"] == "Test Board"
        assert len(result["columns"]) == 1

    def test_parse_with_errors_minimal_board(self, minimal_board_markdown: str):
        """Test parse_with_errors on minimal board."""
        result = BrainfileParser.parse_with_errors(minimal_board_markdown)
        assert result.error is None
        assert result.data is not None
        assert result.type == BrainfileType.BOARD.value
        assert result.renderer == RendererType.KANBAN

    def test_parse_with_errors_journal(self):
        """Test parse_with_errors on journal content."""
        content = """---
title: Daily Journal
type: journal
entries:
  - id: 2026-01-01
    title: Standup
    createdAt: 2026-01-01T09:00:00Z
---
"""
        result = BrainfileParser.parse_with_errors(content)
        assert result.error is None
        assert result.data is not None
        assert result.type == BrainfileType.JOURNAL.value
        assert result.renderer == RendererType.TIMELINE
        assert len(result.data["entries"]) == 1

    def test_parse_missing_frontmatter_start(self):
        """Test parsing content without frontmatter start."""
        content = """title: Test
columns: []
---
"""
        result = BrainfileParser.parse(content)
        assert result is None

    def test_parse_missing_frontmatter_end(self):
        """Test parsing content without frontmatter end."""
        content = """---
title: Test
columns: []
"""
        result = BrainfileParser.parse(content)
        assert result is None

    def test_parse_with_errors_invalid_yaml(self):
        """Test parse_with_errors with invalid YAML."""
        content = """---
title: Test
columns:
  - id: todo
    title: Invalid: Unquoted: Content
---
"""
        # May succeed depending on YAML parser tolerance
        # The important thing is it doesn't crash
        BrainfileParser.parse_with_errors(content)

    def test_parse_empty_board(self):
        """Test parsing a board with no tasks."""
        content = """---
title: Empty Board
columns:
  - id: backlog
    title: Backlog
    tasks: []
---
"""
        result = BrainfileParser.parse(content)
        assert result is not None
        assert result["title"] == "Empty Board"
        assert result["columns"][0]["tasks"] == []

    def test_parse_complex_board(self):
        """Test parsing a complex board with all features."""
        content = """---
title: Complex Board
protocolVersion: "1.0"
agent:
  instructions:
    - Test instruction
rules:
  always:
    - id: 1
      rule: Always test
columns:
  - id: todo
    title: To Do
    tasks:
      - id: task-1
        title: Test Task
        description: Description
        priority: high
        tags:
          - urgent
        subtasks:
          - id: task-1-1
            title: Subtask 1
            completed: false
---
"""
        result = BrainfileParser.parse_with_errors(content)
        assert result.error is None
        assert result.data is not None
        assert result.data["protocolVersion"] == "1.0"
        assert result.data.get("agent") is not None
        assert result.data.get("rules") is not None

    def test_parse_duplicate_columns(self):
        """Test that duplicate columns are consolidated."""
        content = """---
title: Test Board
columns:
  - id: todo
    title: To Do
    tasks:
      - id: task-1
        title: Task 1
  - id: todo
    title: To Do (duplicate)
    tasks:
      - id: task-2
        title: Task 2
---
"""
        result = BrainfileParser.parse_with_errors(content)
        assert result.data is not None
        assert len(result.data["columns"]) == 1
        assert result.warnings is not None
        assert any("Duplicate" in w for w in result.warnings)


class TestFindTaskLocation:
    """Tests for find_task_location."""

    def test_find_task_location(self):
        """Test finding a task's location in content."""
        content = """---
title: Test Board
columns:
  - id: todo
    title: To Do
    tasks:
      - id: task-1
        title: First Task
      - id: task-2
        title: Second Task
---
"""
        location = BrainfileParser.find_task_location(content, "task-1")
        assert location is not None
        line, col = location
        assert line > 0

    def test_find_task_location_not_found(self):
        """Test finding a non-existent task."""
        content = """---
title: Test Board
columns: []
---
"""
        location = BrainfileParser.find_task_location(content, "task-999")
        assert location is None


class TestFindRuleLocation:
    """Tests for find_rule_location."""

    def test_find_rule_location(self):
        """Test finding a rule's location in content."""
        content = """---
title: Test Board
rules:
  always:
    - id: 1
      rule: Always test
    - id: 2
      rule: Always document
columns: []
---
"""
        location = BrainfileParser.find_rule_location(content, 1, "always")
        assert location is not None
        line, col = location
        assert line > 0

    def test_find_rule_location_not_found(self):
        """Test finding a non-existent rule."""
        content = """---
title: Test Board
columns: []
---
"""
        location = BrainfileParser.find_rule_location(content, 1, "always")
        assert location is None
