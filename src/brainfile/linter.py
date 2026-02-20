"""
Linter for Brainfile markdown files with YAML frontmatter.

This module provides linting functionality for brainfile.md files,
checking for YAML syntax errors, structural issues, and providing auto-fix.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import StringIO
from typing import Literal

from ruamel.yaml import YAML

from .models import Board
from .parser import BrainfileParser
from .validator import BrainfileValidator


@dataclass
class LintIssue:
    """A lint issue (error or warning)."""

    type: Literal["error", "warning"]
    message: str
    line: int | None = None
    column: int | None = None
    fixable: bool = False
    code: str | None = None
    """Error code for categorization"""


@dataclass
class LintResult:
    """Result of linting a brainfile."""

    valid: bool
    issues: list[LintIssue] = field(default_factory=list)
    fixed_content: str | None = None
    board: Board | None = None


@dataclass
class LintOptions:
    """Options for linting."""

    auto_fix: bool = False
    strict_mode: bool = False
    """If True, warnings are treated as errors"""


class BrainfileLinter:
    """Linter for Brainfile markdown files with YAML frontmatter."""

    @staticmethod
    def lint(content: str, options: LintOptions | None = None) -> LintResult:
        """
        Lint a brainfile.md content string.

        Args:
            content: The markdown content with YAML frontmatter
            options: Linting options

        Returns:
            LintResult with issues and optionally fixed content
        """
        if options is None:
            options = LintOptions()

        issues: list[LintIssue] = []
        fixed_content = content
        board: Board | None = None

        # Step 1: Check for fixable YAML issues (unquoted strings with colons)
        quotable_strings = BrainfileLinter._find_unquoted_strings_with_colons(content)
        if quotable_strings:
            for item in quotable_strings:
                issues.append(
                    LintIssue(
                        type="warning",
                        message=f'Unquoted string with colon: "{item["text"]}"',
                        line=item["line"],
                        fixable=True,
                        code="UNQUOTED_STRING",
                    )
                )

            if options.auto_fix:
                fixed_content = BrainfileLinter._fix_unquoted_strings(
                    content, quotable_strings
                )

        # Step 2: Check YAML syntax
        content_to_validate = (
            fixed_content if options.auto_fix and fixed_content != content else content
        )
        yaml_issues = BrainfileLinter._check_yaml_syntax(content_to_validate)

        # If we applied fixes, check if the issues still exist
        if options.auto_fix and fixed_content != content:
            remaining_yaml_issues = BrainfileLinter._check_yaml_syntax(fixed_content)
            issues.extend(remaining_yaml_issues)
        else:
            issues.extend(yaml_issues)

        # Step 3: Validate board structure (if YAML is valid)
        final_yaml_issues = (
            BrainfileLinter._check_yaml_syntax(fixed_content)
            if options.auto_fix
            else yaml_issues
        )
        if not final_yaml_issues:
            result = BrainfileParser.parse_with_errors(
                fixed_content if options.auto_fix else content
            )

            if result.board:
                board = result.board

                # Check for duplicate column IDs (informational - already handled by parser)
                if result.warnings:
                    for warning in result.warnings:
                        # Match both the header and individual warnings
                        if "Duplicate column" in warning:
                            # Skip the header line, only process actual duplicate messages
                            if "Duplicate columns detected:" not in warning:
                                clean_message = (
                                    warning.replace("[Brainfile Parser]", "")
                                    .lstrip()
                                    .lstrip("-")
                                    .strip()
                                )

                                if clean_message:
                                    issues.append(
                                        LintIssue(
                                            type="warning",
                                            message=clean_message,
                                            fixable=False,
                                            code="DUPLICATE_COLUMN",
                                        )
                                    )

                # Run structural validation
                validation = BrainfileValidator.validate(result.board)
                if not validation.valid:
                    for err in validation.errors:
                        issues.append(
                            LintIssue(
                                type="error",
                                message=f"{err.path}: {err.message}",
                                fixable=False,
                                code="VALIDATION_ERROR",
                            )
                        )
            elif result.error:
                issues.append(
                    LintIssue(
                        type="error",
                        message=f"Parse error: {result.error}",
                        fixable=False,
                        code="PARSE_ERROR",
                    )
                )

        # Determine if valid (no errors, or only warnings in non-strict mode)
        has_errors = any(i.type == "error" for i in issues)
        has_warnings = any(i.type == "warning" for i in issues)
        valid = not has_errors and not has_warnings if options.strict_mode else not has_errors

        return LintResult(
            valid=valid,
            issues=issues,
            fixed_content=fixed_content if options.auto_fix and fixed_content != content else None,
            board=board,
        )

    @staticmethod
    def _check_yaml_syntax(content: str) -> list[LintIssue]:
        """Check YAML syntax by attempting to parse."""
        issues: list[LintIssue] = []

        try:
            lines = content.split("\n")

            # Find frontmatter boundaries
            if not lines[0].strip().startswith("---"):
                issues.append(
                    LintIssue(
                        type="error",
                        message="Missing YAML frontmatter opening (---)",
                        line=1,
                        fixable=False,
                        code="MISSING_FRONTMATTER_START",
                    )
                )
                return issues

            end_index = -1
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    end_index = i
                    break

            if end_index == -1:
                issues.append(
                    LintIssue(
                        type="error",
                        message="Missing YAML frontmatter closing (---)",
                        fixable=False,
                        code="MISSING_FRONTMATTER_END",
                    )
                )
                return issues

            # Extract and parse YAML
            yaml_content = "\n".join(lines[1:end_index])
            yaml = YAML()
            yaml.load(StringIO(yaml_content))

        except Exception as error:
            # Check for ruamel.yaml error format
            if hasattr(error, "context_mark") or hasattr(error, "problem_mark"):
                mark = getattr(error, "problem_mark", None) or getattr(
                    error, "context_mark", None
                )
                if mark:
                    issues.append(
                        LintIssue(
                            type="error",
                            message=f"YAML syntax error: {error}",
                            line=mark.line + 2,  # Adjust for frontmatter offset
                            column=mark.column,
                            fixable=False,
                            code="YAML_SYNTAX_ERROR",
                        )
                    )
                else:
                    issues.append(
                        LintIssue(
                            type="error",
                            message=f"YAML error: {error}",
                            fixable=False,
                            code="YAML_ERROR",
                        )
                    )
            else:
                issues.append(
                    LintIssue(
                        type="error",
                        message=f"YAML error: {error}",
                        fixable=False,
                        code="YAML_ERROR",
                    )
                )

        return issues

    @staticmethod
    def _find_unquoted_strings_with_colons(
        content: str,
    ) -> list[dict[str, str | int]]:
        """Find strings with colons that should be quoted."""
        results: list[dict[str, str | int]] = []
        lines = content.split("\n")

        # Look for title: or rule: fields with unquoted strings containing colons
        title_pattern = re.compile(
            r'^(\s+)(title|rule|description):\s+([^"\'"][^"\n]*:\s*[^"\n]+)$'
        )

        for index, line in enumerate(lines):
            match = title_pattern.match(line)
            if match:
                text = match.group(3).strip()
                # Check if it contains a colon followed by space (YAML separator)
                if ": " in text:
                    results.append(
                        {
                            "line": index + 1,
                            "text": text,
                            "full_line": line,
                        }
                    )

        return results

    @staticmethod
    def _fix_unquoted_strings(
        content: str,
        issues: list[dict[str, str | int]],
    ) -> str:
        """Fix unquoted strings by adding quotes."""
        lines = content.split("\n")

        for issue in issues:
            line_index = int(issue["line"]) - 1
            line = lines[line_index]

            # Match the pattern and replace with quoted version
            match = re.match(r"^(\s+)(title|rule|description):\s+(.+)$", line)
            if match:
                indent = match.group(1)
                key = match.group(2)
                value = match.group(3).strip()

                # Only quote if not already quoted
                if not value.startswith('"') and not value.startswith("'"):
                    lines[line_index] = f'{indent}{key}: "{value}"'

        return "\n".join(lines)

    @staticmethod
    def get_summary(result: LintResult) -> str:
        """
        Get a human-readable summary of lint results.

        Args:
            result: The lint result to summarize

        Returns:
            Human-readable summary string
        """
        if result.valid and not result.issues:
            return "No issues found"

        errors = [i for i in result.issues if i.type == "error"]
        warnings = [i for i in result.issues if i.type == "warning"]
        fixable = [i for i in result.issues if i.fixable]

        parts: list[str] = []

        if errors:
            parts.append(f"{len(errors)} error{'s' if len(errors) > 1 else ''}")

        if warnings:
            parts.append(f"{len(warnings)} warning{'s' if len(warnings) > 1 else ''}")

        if fixable:
            parts.append(f"{len(fixable)} fixable")

        return ", ".join(parts)

    @staticmethod
    def group_issues(
        result: LintResult,
    ) -> dict[str, list[LintIssue]]:
        """
        Get issues grouped by type.

        Args:
            result: The lint result to group

        Returns:
            Dictionary with errors, warnings, and fixable issues
        """
        return {
            "errors": [i for i in result.issues if i.type == "error"],
            "warnings": [i for i in result.issues if i.type == "warning"],
            "fixable": [i for i in result.issues if i.fixable],
        }
