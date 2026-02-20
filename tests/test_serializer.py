"""Tests for the serializer module."""

import pytest

from brainfile import (
    Board,
    BrainfileParser,
    BrainfileSerializer,
    Column,
    SerializeOptions,
    Task,
)


class TestBrainfileSerializer:
    """Tests for BrainfileSerializer."""

    def test_serialize_minimal_board(self, minimal_board: Board):
        """Test serializing a minimal board."""
        result = BrainfileSerializer.serialize(minimal_board)
        assert result.startswith("---\n")
        assert result.endswith("---\n")
        assert "title: Test Board" in result

    def test_serialize_complex_board(self, complex_board: Board):
        """Test serializing a complex board."""
        result = BrainfileSerializer.serialize(complex_board)
        assert "Complex Board" in result
        assert "protocolVersion" in result
        assert "instructions" in result
        assert "rules" in result

    def test_serialize_with_options(self, minimal_board: Board):
        """Test serializing with custom options."""
        options = SerializeOptions(
            indent=4,
            trailing_newline=False,
        )
        result = BrainfileSerializer.serialize(minimal_board, options)
        # Check for 4-space indentation
        assert "    " in result
        # Should not end with newline
        assert not result.endswith("\n")

    def test_serialize_yaml_only(self, minimal_board: Board):
        """Test serializing to YAML only (without frontmatter wrapper)."""
        result = BrainfileSerializer.serialize_yaml_only(minimal_board)
        assert not result.startswith("---")
        assert "title: Test Board" in result

    def test_pretty_print(self, minimal_board: Board):
        """Test pretty printing to JSON."""
        result = BrainfileSerializer.pretty_print(minimal_board)
        assert '"title": "Test Board"' in result

    def test_roundtrip_minimal(self, minimal_board: Board):
        """Test that serialize/parse roundtrip preserves data."""
        serialized = BrainfileSerializer.serialize(minimal_board)
        parsed = BrainfileParser.parse_with_errors(serialized)
        assert parsed.board is not None
        assert parsed.board.title == minimal_board.title
        assert len(parsed.board.columns) == len(minimal_board.columns)

    def test_roundtrip_complex(self, complex_board: Board):
        """Test roundtrip with complex board."""
        serialized = BrainfileSerializer.serialize(complex_board)
        parsed = BrainfileParser.parse_with_errors(serialized)
        assert parsed.board is not None
        assert parsed.board.title == complex_board.title
        assert parsed.board.protocol_version == complex_board.protocol_version

    def test_serialize_from_dict(self, minimal_board_dict: dict):
        """Test serializing from a plain dict."""
        result = BrainfileSerializer.serialize(minimal_board_dict)
        assert "title: Test Board" in result

    def test_serialize_preserves_aliases(self):
        """Test that serialization uses camelCase aliases."""
        board = Board(
            title="Test",
            columns=[
                Column(
                    id="todo",
                    title="To Do",
                    tasks=[
                        Task(
                            id="task-1",
                            title="Test",
                            due_date="2024-12-31",
                            related_files=["file.py"],
                        ),
                    ],
                ),
            ],
        )
        result = BrainfileSerializer.serialize(board)
        assert "dueDate" in result
        assert "relatedFiles" in result
        # Should NOT contain snake_case versions
        assert "due_date" not in result
        assert "related_files" not in result
