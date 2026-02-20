"""Tests for the linter module."""

import pytest

from brainfile import (
    BrainfileLinter,
    LintIssue,
    LintOptions,
    LintResult,
)


class TestBrainfileLinter:
    """Tests for BrainfileLinter."""

    def test_lint_valid_content(self, minimal_board_markdown: str):
        """Test linting valid content."""
        result = BrainfileLinter.lint(minimal_board_markdown)
        assert result.valid is True
        assert len(result.issues) == 0

    def test_lint_missing_frontmatter_start(self):
        """Test linting content without frontmatter start."""
        content = """title: Test
columns: []
---
"""
        result = BrainfileLinter.lint(content)
        assert result.valid is False
        assert any("MISSING_FRONTMATTER_START" == i.code for i in result.issues)

    def test_lint_missing_frontmatter_end(self):
        """Test linting content without frontmatter end."""
        content = """---
title: Test
columns: []
"""
        result = BrainfileLinter.lint(content)
        assert result.valid is False
        assert any("MISSING_FRONTMATTER_END" == i.code for i in result.issues)

    def test_lint_yaml_syntax_error(self):
        """Test linting content with YAML syntax error."""
        content = """---
title: Test
columns:
  - id: todo
    title: To Do
    tasks:
      - id: task-1
        title: Invalid: Unquoted: Content
---
"""
        result = BrainfileLinter.lint(content)
        # May have warnings or errors depending on YAML parser tolerance
        # The important thing is it doesn't crash

    def test_lint_unquoted_string_with_colon(self):
        """Test detecting unquoted strings with colons."""
        content = """---
title: Test Board
columns:
  - id: todo
    title: To Do
    tasks:
      - id: task-1
        title: Bug: Something is broken
---
"""
        result = BrainfileLinter.lint(content)
        # Should detect the unquoted string warning
        warnings = [i for i in result.issues if i.type == "warning"]
        assert any("UNQUOTED_STRING" == i.code for i in warnings)

    def test_lint_auto_fix_unquoted_string(self):
        """Test auto-fixing unquoted strings with colons."""
        content = """---
title: Test Board
columns:
  - id: todo
    title: To Do
    tasks:
      - id: task-1
        title: Bug: Something is broken
---
"""
        options = LintOptions(auto_fix=True)
        result = BrainfileLinter.lint(content, options)
        assert result.fixed_content is not None
        assert '"Bug: Something is broken"' in result.fixed_content

    def test_lint_strict_mode(self):
        """Test that strict mode treats warnings as errors."""
        content = """---
title: Test Board
columns:
  - id: todo
    title: To Do
    tasks:
      - id: task-1
        title: Bug: Something is broken
---
"""
        # Without strict mode
        result_normal = BrainfileLinter.lint(content, LintOptions(strict_mode=False))

        # With strict mode
        result_strict = BrainfileLinter.lint(content, LintOptions(strict_mode=True))

        # In strict mode, warnings make it invalid
        if any(i.type == "warning" for i in result_normal.issues):
            assert result_strict.valid is False

    def test_lint_duplicate_columns(self):
        """Test detecting duplicate columns."""
        content = """---
title: Test Board
columns:
  - id: todo
    title: To Do
    tasks: []
  - id: todo
    title: To Do Duplicate
    tasks: []
---
"""
        result = BrainfileLinter.lint(content)
        # Should have a warning about duplicate columns
        warnings = [i for i in result.issues if i.type == "warning"]
        assert any("DUPLICATE_COLUMN" == i.code for i in warnings)

    def test_lint_validation_error(self):
        """Test detecting validation errors."""
        content = """---
title: Test Board
columns:
  - id: todo
    title: To Do
    tasks:
      - id: task-1
        title: ""
---
"""
        result = BrainfileLinter.lint(content)
        # Should have validation errors for empty title
        errors = [i for i in result.issues if i.type == "error"]
        # Empty title should be caught by validator
        assert any("VALIDATION_ERROR" == i.code for i in errors)


class TestGetSummary:
    """Tests for get_summary."""

    def test_summary_no_issues(self):
        """Test summary with no issues."""
        result = LintResult(valid=True, issues=[])
        summary = BrainfileLinter.get_summary(result)
        assert summary == "No issues found"

    def test_summary_errors_only(self):
        """Test summary with errors only."""
        result = LintResult(
            valid=False,
            issues=[
                LintIssue(type="error", message="Error 1"),
                LintIssue(type="error", message="Error 2"),
            ],
        )
        summary = BrainfileLinter.get_summary(result)
        assert "2 errors" in summary

    def test_summary_warnings_only(self):
        """Test summary with warnings only."""
        result = LintResult(
            valid=True,
            issues=[
                LintIssue(type="warning", message="Warning 1"),
            ],
        )
        summary = BrainfileLinter.get_summary(result)
        assert "1 warning" in summary

    def test_summary_mixed(self):
        """Test summary with mixed issues."""
        result = LintResult(
            valid=False,
            issues=[
                LintIssue(type="error", message="Error 1"),
                LintIssue(type="warning", message="Warning 1", fixable=True),
                LintIssue(type="warning", message="Warning 2", fixable=True),
            ],
        )
        summary = BrainfileLinter.get_summary(result)
        assert "1 error" in summary
        assert "2 warnings" in summary
        assert "2 fixable" in summary


class TestGroupIssues:
    """Tests for group_issues."""

    def test_group_issues(self):
        """Test grouping issues by type."""
        result = LintResult(
            valid=False,
            issues=[
                LintIssue(type="error", message="Error 1"),
                LintIssue(type="warning", message="Warning 1", fixable=True),
                LintIssue(type="warning", message="Warning 2"),
                LintIssue(type="error", message="Error 2", fixable=True),
            ],
        )
        groups = BrainfileLinter.group_issues(result)

        assert len(groups["errors"]) == 2
        assert len(groups["warnings"]) == 2
        assert len(groups["fixable"]) == 2

    def test_group_empty(self):
        """Test grouping empty issues."""
        result = LintResult(valid=True, issues=[])
        groups = BrainfileLinter.group_issues(result)

        assert len(groups["errors"]) == 0
        assert len(groups["warnings"]) == 0
        assert len(groups["fixable"]) == 0


class TestLintIssue:
    """Tests for LintIssue dataclass."""

    def test_issue_with_location(self):
        """Test issue with line and column."""
        issue = LintIssue(
            type="error",
            message="Test error",
            line=10,
            column=5,
            fixable=False,
            code="TEST_ERROR",
        )
        assert issue.type == "error"
        assert issue.message == "Test error"
        assert issue.line == 10
        assert issue.column == 5
        assert issue.fixable is False
        assert issue.code == "TEST_ERROR"

    def test_issue_defaults(self):
        """Test issue with default values."""
        issue = LintIssue(type="warning", message="Test warning")
        assert issue.line is None
        assert issue.column is None
        assert issue.fixable is False
        assert issue.code is None


class TestLintOptions:
    """Tests for LintOptions dataclass."""

    def test_options_defaults(self):
        """Test options with default values."""
        options = LintOptions()
        assert options.auto_fix is False
        assert options.strict_mode is False

    def test_options_custom(self):
        """Test options with custom values."""
        options = LintOptions(auto_fix=True, strict_mode=True)
        assert options.auto_fix is True
        assert options.strict_mode is True
