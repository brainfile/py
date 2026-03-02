"""Tests for board config file I/O (parse, serialize, read, write)."""

import os
import tempfile

import pytest

from brainfile import (
    AgentInstructions,
    BoardConfig,
    ColumnConfig,
    parse_board_config,
    read_board_config,
    serialize_board_config,
    write_board_config,
)


MINIMAL_CONFIG = BoardConfig(
    title="Test Board",
    columns=[
        ColumnConfig(id="todo", title="To Do"),
        ColumnConfig(id="done", title="Done", completion_column=True),
    ],
)


class TestParseBoardConfig:
    """Tests for parse_board_config."""

    def test_parse_minimal(self):
        content = (
            "---\n"
            "title: Test Board\n"
            "columns:\n"
            "- id: todo\n"
            "  title: To Do\n"
            "---\n"
        )
        config, body = parse_board_config(content)
        assert config.title == "Test Board"
        assert len(config.columns) == 1
        assert config.columns[0].id == "todo"
        assert body == ""

    def test_parse_with_body(self):
        content = (
            "---\n"
            "title: Test Board\n"
            "columns:\n"
            "- id: todo\n"
            "  title: To Do\n"
            "---\n"
            "\n"
            "## Notes\n"
            "Some project notes here.\n"
        )
        config, body = parse_board_config(content)
        assert config.title == "Test Board"
        assert "## Notes" in body
        assert "Some project notes here." in body

    def test_parse_with_agent_identity(self):
        content = (
            "---\n"
            "title: Test Board\n"
            "columns:\n"
            "- id: todo\n"
            "  title: To Do\n"
            "agent:\n"
            "  instructions:\n"
            "  - Always write tests\n"
            "  identity: You are a senior engineer\n"
            "---\n"
        )
        config, body = parse_board_config(content)
        assert config.agent is not None
        assert config.agent.identity == "You are a senior engineer"
        assert config.agent.instructions == ["Always write tests"]

    def test_parse_raises_on_no_frontmatter(self):
        with pytest.raises(ValueError, match="does not start with"):
            parse_board_config("Just plain text")

    def test_parse_raises_on_no_closing_delimiter(self):
        with pytest.raises(ValueError, match="Missing closing"):
            parse_board_config("---\ntitle: Test\n")

    def test_parse_raises_on_empty_yaml(self):
        with pytest.raises(ValueError, match="empty"):
            parse_board_config("---\n---\n")

    def test_parse_round_trip(self):
        """parse -> serialize -> parse produces equivalent config."""
        content = (
            "---\n"
            "title: Round Trip\n"
            "type: board\n"
            "columns:\n"
            "- id: todo\n"
            "  title: To Do\n"
            "- id: done\n"
            "  title: Done\n"
            "  completionColumn: true\n"
            "agent:\n"
            "  instructions:\n"
            "  - Be concise\n"
            "  identity: You are a task manager\n"
            "---\n"
            "\n"
            "## Notes\n"
            "Some notes.\n"
        )
        config, body = parse_board_config(content)
        serialized = serialize_board_config(config, body)
        config2, body2 = parse_board_config(serialized)

        assert config2.title == config.title
        assert config2.type == config.type
        assert len(config2.columns) == len(config.columns)
        assert config2.columns[0].id == config.columns[0].id
        assert config2.columns[1].completion_column == config.columns[1].completion_column
        assert config2.agent.identity == config.agent.identity
        assert config2.agent.instructions == config.agent.instructions
        assert "Some notes." in body2


class TestSerializeBoardConfig:
    """Tests for serialize_board_config."""

    def test_serialize_minimal(self):
        result = serialize_board_config(MINIMAL_CONFIG)
        assert result.startswith("---\n")
        assert "title: Test Board" in result
        assert "---\n" in result
        # Should end with closing delimiter since no body
        assert result.endswith("---\n")

    def test_serialize_with_body(self):
        result = serialize_board_config(MINIMAL_CONFIG, "## Notes\nHello\n")
        assert "---\n\n## Notes" in result
        assert result.endswith("Hello\n")

    def test_serialize_adds_trailing_newline_to_body(self):
        result = serialize_board_config(MINIMAL_CONFIG, "No trailing newline")
        assert result.endswith("No trailing newline\n")

    def test_serialize_uses_camel_case(self):
        config = BoardConfig(
            title="Test",
            columns=[
                ColumnConfig(id="done", title="Done", completion_column=True),
            ],
        )
        result = serialize_board_config(config)
        assert "completionColumn:" in result
        # Should NOT contain snake_case
        assert "completion_column:" not in result

    def test_serialize_with_agent_identity(self):
        config = BoardConfig(
            title="Test",
            columns=[ColumnConfig(id="todo", title="To Do")],
            agent=AgentInstructions(
                instructions=["Write tests"],
                identity="You are a senior backend engineer",
            ),
        )
        result = serialize_board_config(config)
        assert "identity: You are a senior backend engineer" in result

    def test_serialize_excludes_none(self):
        config = BoardConfig(
            title="Test",
            columns=[ColumnConfig(id="todo", title="To Do")],
        )
        result = serialize_board_config(config)
        # agent is None, should not appear
        assert "agent:" not in result
        # rules is None, should not appear
        assert "rules:" not in result

    def test_serialize_empty_body(self):
        result = serialize_board_config(MINIMAL_CONFIG, "")
        # No blank line or body section
        assert result.endswith("---\n")


class TestAgentInstructionsExtensionFields:
    """Extension fields on AgentInstructions survive round-trip."""

    def test_agent_extras_round_trip(self):
        content = (
            "---\n"
            "title: Test Board\n"
            "columns:\n"
            "- id: todo\n"
            "  title: To Do\n"
            "agent:\n"
            "  instructions:\n"
            "  - Be concise\n"
            "  x-otto:\n"
            "    model: gpt-4\n"
            "    temperature: 0.7\n"
            "---\n"
        )
        config, body = parse_board_config(content)
        assert config.agent._extras == {"x-otto": {"model": "gpt-4", "temperature": 0.7}}

        serialized = serialize_board_config(config, body)
        assert "x-otto:" in serialized

        config2, _ = parse_board_config(serialized)
        assert config2.agent._extras["x-otto"] == {"model": "gpt-4", "temperature": 0.7}


class TestBoardConfigExtensionFields:
    """Extension fields on BoardConfig survive round-trip."""

    def test_board_config_extras_round_trip(self):
        content = (
            "---\n"
            "title: Test Board\n"
            "columns:\n"
            "- id: todo\n"
            "  title: To Do\n"
            "x-custom:\n"
            "  setting: enabled\n"
            "---\n"
        )
        config, body = parse_board_config(content)
        assert config._extras == {"x-custom": {"setting": "enabled"}}

        serialized = serialize_board_config(config, body)
        assert "x-custom:" in serialized

        config2, _ = parse_board_config(serialized)
        assert config2._extras["x-custom"] == {"setting": "enabled"}


class TestWriteReadBoardConfig:
    """Tests for write_board_config / read_board_config file round-trip."""

    def test_write_read_round_trip(self, tmp_path):
        file_path = str(tmp_path / "brainfile.md")

        config = BoardConfig(
            title="Write Test",
            columns=[
                ColumnConfig(id="todo", title="To Do"),
                ColumnConfig(id="in-progress", title="In Progress"),
                ColumnConfig(id="done", title="Done", completion_column=True),
            ],
            agent=AgentInstructions(
                instructions=["Always write tests", "Use type hints"],
                identity="You are a Python expert",
            ),
        )
        body = "## Notes\nProject-level notes.\n"

        write_board_config(file_path, config, body)

        # Verify file exists
        assert os.path.exists(file_path)

        # Read back with existing read_board_config (compatibility)
        read_config = read_board_config(file_path)
        assert read_config.title == "Write Test"
        assert len(read_config.columns) == 3
        assert read_config.agent.identity == "You are a Python expert"

        # Read back with parse_board_config for full round-trip
        with open(file_path, encoding="utf-8") as f:
            raw = f.read()
        config2, body2 = parse_board_config(raw)
        assert config2.title == "Write Test"
        assert "Project-level notes." in body2

    def test_write_creates_parent_dirs(self, tmp_path):
        file_path = str(tmp_path / "nested" / "deep" / "brainfile.md")

        write_board_config(file_path, MINIMAL_CONFIG)

        assert os.path.exists(file_path)
        config = read_board_config(file_path)
        assert config.title == "Test Board"

    def test_write_read_empty_body(self, tmp_path):
        file_path = str(tmp_path / "brainfile.md")

        write_board_config(file_path, MINIMAL_CONFIG)

        with open(file_path, encoding="utf-8") as f:
            raw = f.read()
        config, body = parse_board_config(raw)
        assert config.title == "Test Board"
        assert body == ""

    def test_write_read_with_extension_fields(self, tmp_path):
        file_path = str(tmp_path / "brainfile.md")

        agent = AgentInstructions.model_validate({
            "instructions": ["Be fast"],
            "identity": "Speed daemon",
            "x-otto": {"model": "gpt-4o", "chain": ["think", "act"]},
        })
        config = BoardConfig.model_validate({
            "title": "Extensions Test",
            "columns": [{"id": "todo", "title": "To Do"}],
            "agent": agent.model_dump(by_alias=True),
            "x-custom": {"version": 2},
        })

        write_board_config(file_path, config)

        with open(file_path, encoding="utf-8") as f:
            raw = f.read()
        config2, _ = parse_board_config(raw)
        assert config2.agent._extras["x-otto"] == {"model": "gpt-4o", "chain": ["think", "act"]}
        assert config2._extras["x-custom"] == {"version": 2}
        assert config2.agent.identity == "Speed daemon"
