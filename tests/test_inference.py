"""Tests for the inference module."""

import pytest

from brainfile import (
    BrainfileType,
    RendererType,
    infer_renderer,
    infer_type,
)
from brainfile.schema_hints import SchemaHints

# Note: SchemaHints tests have been moved to test_schema_hints.py
# This file focuses on type and renderer inference logic


class TestInferType:
    """Tests for infer_type."""

    def test_explicit_type_field(self):
        """Test inference from explicit type field."""
        data = {"type": "journal", "title": "My Journal", "entries": []}
        result = infer_type(data)
        assert result == "journal"

    def test_schema_url_pattern(self):
        """Test inference from schema URL."""
        data = {"schema": "https://example.com/v1/journal.json", "title": "Test"}
        result = infer_type(data)
        assert result == "journal"

    def test_filename_suffix(self):
        """Test inference from filename suffix."""
        data = {"title": "My Journal"}
        result = infer_type(data, "brainfile.journal.md")
        assert result == "journal"

    def test_structure_board(self):
        """Test inference from board structure."""
        data = {"title": "Board", "columns": []}
        result = infer_type(data)
        assert result == BrainfileType.BOARD.value

    def test_structure_journal(self):
        """Test inference from journal structure."""
        data = {"title": "Journal", "entries": []}
        result = infer_type(data)
        assert result == BrainfileType.JOURNAL.value

    def test_structure_collection(self):
        """Test inference from collection structure."""
        data = {"title": "Collection", "categories": []}
        result = infer_type(data)
        assert result == BrainfileType.COLLECTION.value

    def test_structure_checklist(self):
        """Test inference from checklist structure."""
        data = {
            "title": "Checklist",
            "items": [
                {"id": "1", "title": "Item 1", "completed": False},
                {"id": "2", "title": "Item 2", "completed": True},
            ],
        }
        result = infer_type(data)
        assert result == BrainfileType.CHECKLIST.value

    def test_structure_document(self):
        """Test inference from document structure."""
        data = {"title": "Document", "sections": []}
        result = infer_type(data)
        assert result == BrainfileType.DOCUMENT.value

    def test_default_board(self):
        """Test default inference returns board."""
        data = {"title": "Unknown"}
        result = infer_type(data)
        assert result == BrainfileType.BOARD.value

    def test_non_dict_data(self):
        """Test inference with non-dict data."""
        result = infer_type("not a dict")
        assert result == BrainfileType.BOARD.value

    def test_priority_explicit_over_structure(self):
        """Test that explicit type takes priority over structure."""
        data = {"type": "custom", "columns": [], "title": "Test"}
        result = infer_type(data)
        assert result == "custom"

    def test_priority_schema_over_filename(self):
        """Test that schema URL takes priority over filename."""
        data = {"schema": "https://example.com/v1/checklist.json", "title": "Test"}
        result = infer_type(data, "brainfile.journal.md")
        assert result == "checklist"


class TestInferRenderer:
    """Tests for infer_renderer."""

    def test_schema_hint_override(self):
        """Test that schema hint takes priority."""
        hints = SchemaHints(renderer="timeline")
        data = {"columns": []}  # Would normally be kanban
        result = infer_renderer("board", data, hints)
        assert result == RendererType.TIMELINE

    def test_invalid_schema_hint(self):
        """Test that invalid schema hint falls back to structure."""
        hints = SchemaHints(renderer="invalid")
        data = {"columns": []}
        result = infer_renderer("board", data, hints)
        assert result == RendererType.KANBAN

    def test_structure_kanban(self):
        """Test renderer inference from columns structure."""
        data = {"columns": []}
        result = infer_renderer("board", data)
        assert result == RendererType.KANBAN

    def test_structure_timeline(self):
        """Test renderer inference from entries with timestamps."""
        data = {
            "entries": [
                {"id": "1", "title": "Entry", "createdAt": "2024-01-01"},
            ]
        }
        result = infer_renderer("journal", data)
        assert result == RendererType.TIMELINE

    def test_structure_timeline_with_timestamp(self):
        """Test renderer inference from entries with timestamp field."""
        data = {
            "entries": [
                {"id": "1", "title": "Entry", "timestamp": "2024-01-01"},
            ]
        }
        result = infer_renderer("journal", data)
        assert result == RendererType.TIMELINE

    def test_structure_checklist(self):
        """Test renderer inference from items with completed."""
        data = {
            "items": [
                {"id": "1", "title": "Item", "completed": False},
            ]
        }
        result = infer_renderer("checklist", data)
        assert result == RendererType.CHECKLIST

    def test_structure_grouped_list(self):
        """Test renderer inference from categories."""
        data = {"categories": []}
        result = infer_renderer("collection", data)
        assert result == RendererType.GROUPED_LIST

    def test_structure_document(self):
        """Test renderer inference from sections."""
        data = {"sections": []}
        result = infer_renderer("document", data)
        assert result == RendererType.DOCUMENT

    def test_fallback_tree(self):
        """Test fallback to tree renderer."""
        data = {"unknown_structure": []}
        result = infer_renderer("unknown", data)
        assert result == RendererType.TREE

    def test_non_dict_data(self):
        """Test inference with non-dict data."""
        result = infer_renderer("unknown", "not a dict")
        assert result == RendererType.TREE

    def test_empty_entries_no_timestamp(self):
        """Test that entries without timestamps don't trigger timeline."""
        data = {
            "entries": [
                {"id": "1", "title": "Entry"},  # No timestamp
            ]
        }
        result = infer_renderer("journal", data)
        # Should fallback since no timestamp fields
        assert result == RendererType.TREE

    def test_items_without_completed(self):
        """Test that items without completed don't trigger checklist."""
        data = {
            "items": [
                {"id": "1", "title": "Item"},  # No completed
            ]
        }
        result = infer_renderer("list", data)
        assert result == RendererType.TREE


class TestRendererType:
    """Tests for RendererType enum."""

    def test_renderer_values(self):
        """Test renderer type enum values."""
        assert RendererType.KANBAN.value == "kanban"
        assert RendererType.TIMELINE.value == "timeline"
        assert RendererType.CHECKLIST.value == "checklist"
        assert RendererType.GROUPED_LIST.value == "grouped-list"
        assert RendererType.TREE.value == "tree"
        assert RendererType.DOCUMENT.value == "document"


class TestBrainfileType:
    """Tests for BrainfileType enum."""

    def test_brainfile_type_values(self):
        """Test brainfile type enum values."""
        assert BrainfileType.BOARD.value == "board"
        assert BrainfileType.JOURNAL.value == "journal"
        assert BrainfileType.CHECKLIST.value == "checklist"
        assert BrainfileType.COLLECTION.value == "collection"
        assert BrainfileType.DOCUMENT.value == "document"
