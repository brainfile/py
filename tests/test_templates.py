"""Tests for the templates module."""

import re
import pytest

from brainfile import (
    BUILT_IN_TEMPLATES,
    Priority,
    TaskTemplate,
    TemplateType,
    generate_subtask_id,
    generate_task_id,
    get_all_template_ids,
    get_template_by_id,
    process_template,
)


class TestGenerateTaskId:
    """Tests for generate_task_id."""

    def test_generates_unique_ids(self):
        """Test that generate_task_id produces unique IDs."""
        id1 = generate_task_id()
        id2 = generate_task_id()
        assert id1 != id2

    def test_format(self):
        """Test that generated ID has correct format."""
        task_id = generate_task_id()
        assert task_id.startswith("task-")
        # Should have timestamp and random suffix
        parts = task_id.split("-")
        assert len(parts) >= 2

    def test_is_string(self):
        """Test that generated ID is a string."""
        task_id = generate_task_id()
        assert isinstance(task_id, str)


class TestGenerateSubtaskId:
    """Tests for generate_subtask_id."""

    def test_generates_subtask_id(self):
        """Test generating subtask ID from parent and index."""
        subtask_id = generate_subtask_id("task-1", 0)
        assert subtask_id == "task-1-1"

    def test_increments_index(self):
        """Test that index is incremented (1-based)."""
        assert generate_subtask_id("task-1", 0) == "task-1-1"
        assert generate_subtask_id("task-1", 1) == "task-1-2"
        assert generate_subtask_id("task-1", 2) == "task-1-3"

    def test_with_complex_parent_id(self):
        """Test with complex parent task ID."""
        subtask_id = generate_subtask_id("task-123-abc", 0)
        assert subtask_id == "task-123-abc-1"


class TestGetTemplateById:
    """Tests for get_template_by_id."""

    def test_get_bug_report(self):
        """Test getting bug report template."""
        template = get_template_by_id("bug-report")
        assert template is not None
        assert template.id == "bug-report"
        assert template.name == "Bug Report"
        assert template.is_built_in is True

    def test_get_feature_request(self):
        """Test getting feature request template."""
        template = get_template_by_id("feature-request")
        assert template is not None
        assert template.id == "feature-request"
        assert template.name == "Feature Request"

    def test_get_refactor(self):
        """Test getting refactor template."""
        template = get_template_by_id("refactor")
        assert template is not None
        assert template.id == "refactor"
        assert template.name == "Code Refactor"

    def test_nonexistent_template(self):
        """Test getting non-existent template."""
        template = get_template_by_id("nonexistent")
        assert template is None


class TestGetAllTemplateIds:
    """Tests for get_all_template_ids."""

    def test_returns_all_ids(self):
        """Test that all template IDs are returned."""
        ids = get_all_template_ids()
        assert "bug-report" in ids
        assert "feature-request" in ids
        assert "refactor" in ids

    def test_returns_list(self):
        """Test that result is a list."""
        ids = get_all_template_ids()
        assert isinstance(ids, list)

    def test_matches_built_in_count(self):
        """Test that count matches BUILT_IN_TEMPLATES."""
        ids = get_all_template_ids()
        assert len(ids) == len(BUILT_IN_TEMPLATES)


class TestProcessTemplate:
    """Tests for process_template."""

    def test_process_bug_report(self):
        """Test processing bug report template."""
        template = get_template_by_id("bug-report")
        assert template is not None

        values = {"title": "Login fails", "description": "Users cannot login"}
        result = process_template(template, values)

        assert result["title"] == "Login fails"
        assert "Users cannot login" in result["description"]
        assert "Bug Description" in result["description"]

    def test_process_feature_request(self):
        """Test processing feature request template."""
        template = get_template_by_id("feature-request")
        assert template is not None

        values = {"title": "Dark mode", "description": "Add dark theme support"}
        result = process_template(template, values)

        assert result["title"] == "Dark mode"
        assert "Add dark theme support" in result["description"]

    def test_process_refactor(self):
        """Test processing refactor template."""
        template = get_template_by_id("refactor")
        assert template is not None

        values = {"area": "authentication", "description": "Clean up auth module"}
        result = process_template(template, values)

        assert result["title"] == "Refactor: authentication"
        assert "Clean up auth module" in result["description"]

    def test_generates_new_subtask_ids(self):
        """Test that subtasks get new IDs."""
        template = get_template_by_id("bug-report")
        assert template is not None

        values = {"title": "Test", "description": "Test description"}
        result = process_template(template, values)

        assert "subtasks" in result
        assert len(result["subtasks"]) > 0
        # Subtask IDs should be generated based on new task ID
        for subtask in result["subtasks"]:
            assert "-" in subtask["id"]

    def test_preserves_template_fields(self):
        """Test that template fields are preserved."""
        template = get_template_by_id("bug-report")
        assert template is not None

        values = {"title": "Test", "description": "Test"}
        result = process_template(template, values)

        assert result["priority"] == "high"
        assert "bug" in result["tags"]
        assert "needs-triage" in result["tags"]

    def test_missing_variable_preserved(self):
        """Test that missing variables are preserved as placeholders."""
        template = get_template_by_id("bug-report")
        assert template is not None

        values = {"title": "Test"}  # Missing description
        result = process_template(template, values)

        # Description placeholder should be preserved
        assert "{description}" in result["description"]


class TestBuiltInTemplates:
    """Tests for BUILT_IN_TEMPLATES."""

    def test_all_have_required_fields(self):
        """Test that all templates have required fields."""
        for template in BUILT_IN_TEMPLATES:
            assert template.id is not None
            assert template.name is not None
            assert template.template is not None
            assert template.is_built_in is True

    def test_all_have_variables(self):
        """Test that all templates have variables defined."""
        for template in BUILT_IN_TEMPLATES:
            assert template.variables is not None
            assert len(template.variables) > 0

    def test_bug_report_has_subtasks(self):
        """Test that bug report template has subtasks."""
        template = get_template_by_id("bug-report")
        assert template is not None
        assert template.template.subtasks is not None
        assert len(template.template.subtasks) == 5

    def test_feature_request_has_subtasks(self):
        """Test that feature request template has subtasks."""
        template = get_template_by_id("feature-request")
        assert template is not None
        assert template.template.subtasks is not None
        assert len(template.template.subtasks) == 6

    def test_refactor_has_subtasks(self):
        """Test that refactor template has subtasks."""
        template = get_template_by_id("refactor")
        assert template is not None
        assert template.template.subtasks is not None
        assert len(template.template.subtasks) == 6

    def test_template_priorities(self):
        """Test that templates have appropriate priorities."""
        bug = get_template_by_id("bug-report")
        feature = get_template_by_id("feature-request")
        refactor = get_template_by_id("refactor")

        assert bug is not None
        assert feature is not None
        assert refactor is not None

        assert bug.template.priority == Priority.HIGH
        assert feature.template.priority == Priority.MEDIUM
        assert refactor.template.priority == Priority.LOW

    def test_template_types(self):
        """Test that templates have appropriate template types."""
        bug = get_template_by_id("bug-report")
        feature = get_template_by_id("feature-request")
        refactor = get_template_by_id("refactor")

        assert bug is not None
        assert feature is not None
        assert refactor is not None

        assert bug.template.template == TemplateType.BUG
        assert feature.template.template == TemplateType.FEATURE
        assert refactor.template.template == TemplateType.REFACTOR


class TestTemplateVariables:
    """Tests for template variables."""

    def test_bug_report_variables(self):
        """Test bug report template variables."""
        template = get_template_by_id("bug-report")
        assert template is not None

        var_names = [v.name for v in template.variables]
        assert "title" in var_names
        assert "description" in var_names

    def test_required_variables(self):
        """Test that main variables are required."""
        for template in BUILT_IN_TEMPLATES:
            for var in template.variables:
                if var.name in ("title", "description", "area"):
                    assert var.required is True

    def test_variables_have_descriptions(self):
        """Test that all variables have descriptions."""
        for template in BUILT_IN_TEMPLATES:
            for var in template.variables:
                assert var.description is not None
                assert len(var.description) > 0
