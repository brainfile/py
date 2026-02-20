"""Tests for the schema_hints module."""

import pytest

from brainfile import SchemaHints, parse_schema_hints, load_schema_hints


class TestSchemaHints:
    """Tests for SchemaHints dataclass."""

    def test_defaults(self):
        """Test schema hints with default values."""
        hints = SchemaHints()
        assert hints.renderer is None
        assert hints.columns_path is None
        assert hints.items_path is None
        assert hints.title_field is None
        assert hints.status_field is None
        assert hints.timestamp_field is None

    def test_custom_values(self):
        """Test schema hints with custom values."""
        hints = SchemaHints(
            renderer="kanban",
            columns_path="$.columns",
            items_path="$.columns[*].tasks",
            title_field="title",
            status_field="status",
            timestamp_field="createdAt",
        )
        assert hints.renderer == "kanban"
        assert hints.columns_path == "$.columns"
        assert hints.items_path == "$.columns[*].tasks"
        assert hints.title_field == "title"
        assert hints.status_field == "status"
        assert hints.timestamp_field == "createdAt"


class TestParseSchemaHints:
    """Tests for parse_schema_hints function."""

    def test_parse_empty_schema(self):
        """Test parsing empty schema returns empty hints."""
        hints = parse_schema_hints({})
        assert hints.renderer is None
        assert hints.columns_path is None

    def test_parse_none_schema(self):
        """Test parsing None schema returns empty hints."""
        hints = parse_schema_hints(None)
        assert hints.renderer is None

    def test_parse_non_dict_schema(self):
        """Test parsing non-dict schema returns empty hints."""
        hints = parse_schema_hints("not a dict")
        assert hints.renderer is None

    def test_parse_renderer(self):
        """Test parsing x-brainfile-renderer."""
        schema = {"x-brainfile-renderer": "kanban"}
        hints = parse_schema_hints(schema)
        assert hints.renderer == "kanban"

    def test_parse_columns_path(self):
        """Test parsing x-brainfile-columns-path."""
        schema = {"x-brainfile-columns-path": "$.columns"}
        hints = parse_schema_hints(schema)
        assert hints.columns_path == "$.columns"

    def test_parse_items_path(self):
        """Test parsing x-brainfile-items-path."""
        schema = {"x-brainfile-items-path": "$.columns[*].tasks"}
        hints = parse_schema_hints(schema)
        assert hints.items_path == "$.columns[*].tasks"

    def test_parse_title_field(self):
        """Test parsing x-brainfile-title-field."""
        schema = {"x-brainfile-title-field": "name"}
        hints = parse_schema_hints(schema)
        assert hints.title_field == "name"

    def test_parse_status_field(self):
        """Test parsing x-brainfile-status-field."""
        schema = {"x-brainfile-status-field": "done"}
        hints = parse_schema_hints(schema)
        assert hints.status_field == "done"

    def test_parse_timestamp_field(self):
        """Test parsing x-brainfile-timestamp-field."""
        schema = {"x-brainfile-timestamp-field": "updatedAt"}
        hints = parse_schema_hints(schema)
        assert hints.timestamp_field == "updatedAt"

    def test_parse_all_hints(self):
        """Test parsing all hints at once."""
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Custom Board Schema",
            "x-brainfile-renderer": "timeline",
            "x-brainfile-columns-path": "$.stages",
            "x-brainfile-items-path": "$.stages[*].items",
            "x-brainfile-title-field": "name",
            "x-brainfile-status-field": "completed",
            "x-brainfile-timestamp-field": "timestamp",
        }
        hints = parse_schema_hints(schema)
        assert hints.renderer == "timeline"
        assert hints.columns_path == "$.stages"
        assert hints.items_path == "$.stages[*].items"
        assert hints.title_field == "name"
        assert hints.status_field == "completed"
        assert hints.timestamp_field == "timestamp"

    def test_ignores_non_string_values(self):
        """Test that non-string hint values are ignored."""
        schema = {
            "x-brainfile-renderer": 123,  # Not a string
            "x-brainfile-columns-path": ["not", "string"],  # Not a string
        }
        hints = parse_schema_hints(schema)
        assert hints.renderer is None
        assert hints.columns_path is None

    def test_ignores_empty_strings(self):
        """Test that empty string values are treated as falsy."""
        schema = {
            "x-brainfile-renderer": "",  # Empty string
        }
        hints = parse_schema_hints(schema)
        assert hints.renderer is None


class TestLoadSchemaHints:
    """Tests for load_schema_hints function."""

    def test_load_invalid_url(self):
        """Test loading from invalid URL returns None."""
        result = load_schema_hints("https://invalid-domain-that-does-not-exist.com/schema.json")
        assert result is None

    def test_load_malformed_url(self):
        """Test loading from malformed URL returns None."""
        result = load_schema_hints("not-a-url")
        assert result is None

    # Note: We don't test actual HTTP loading in unit tests
    # Integration tests would cover real schema loading
