"""Tests for the discovery module."""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from brainfile import (
    BRAINFILE_GLOBS,
    BRAINFILE_PATTERNS,
    EXCLUDE_DIRS,
    DiscoveredFile,
    DiscoveryOptions,
    DiscoveryResult,
    discover,
    extract_brainfile_suffix,
    find_nearest_brainfile,
    find_primary_brainfile,
    is_brainfile_name,
)


class TestIsBrainfileName:
    """Tests for is_brainfile_name."""

    def test_standard_names(self):
        """Test standard brainfile names."""
        assert is_brainfile_name("brainfile.md") is True
        assert is_brainfile_name(".brainfile.md") is True
        assert is_brainfile_name(".bb.md") is True

    def test_suffixed_names(self):
        """Test suffixed brainfile names."""
        assert is_brainfile_name("brainfile.private.md") is True
        assert is_brainfile_name("brainfile.work.md") is True
        assert is_brainfile_name("brainfile.personal.md") is True

    def test_non_brainfile_names(self):
        """Test non-brainfile names."""
        assert is_brainfile_name("readme.md") is False
        assert is_brainfile_name("notes.md") is False
        assert is_brainfile_name("brainfile.txt") is False
        assert is_brainfile_name("my-brainfile.md") is False

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert is_brainfile_name("Brainfile.md") is True
        assert is_brainfile_name("BRAINFILE.MD") is True
        assert is_brainfile_name("BrainFile.Private.MD") is True

    def test_with_path(self):
        """Test with full path."""
        assert is_brainfile_name("/path/to/brainfile.md") is True
        assert is_brainfile_name("./brainfile.md") is True


class TestExtractBrainfileSuffix:
    """Tests for extract_brainfile_suffix."""

    def test_extract_suffix(self):
        """Test extracting suffix from suffixed names."""
        assert extract_brainfile_suffix("brainfile.private.md") == "private"
        assert extract_brainfile_suffix("brainfile.work.md") == "work"
        assert extract_brainfile_suffix("brainfile.personal.md") == "personal"

    def test_no_suffix(self):
        """Test names without suffix."""
        assert extract_brainfile_suffix("brainfile.md") is None
        assert extract_brainfile_suffix(".brainfile.md") is None
        assert extract_brainfile_suffix(".bb.md") is None

    def test_non_brainfile(self):
        """Test non-brainfile names."""
        assert extract_brainfile_suffix("readme.md") is None
        assert extract_brainfile_suffix("notes.md") is None

    def test_with_path(self):
        """Test with full path."""
        assert extract_brainfile_suffix("/path/to/brainfile.private.md") == "private"


class TestDiscover:
    """Tests for discover."""

    def test_discover_empty_directory(self, tmp_path):
        """Test discovering in empty directory."""
        result = discover(str(tmp_path))
        assert result.root == str(tmp_path)
        assert len(result.files) == 0
        assert result.total_items == 0

    def test_discover_single_brainfile(self, tmp_path):
        """Test discovering a single brainfile."""
        brainfile = tmp_path / "brainfile.md"
        brainfile.write_text("""---
title: Test Board
columns:
  - id: todo
    title: To Do
    tasks: []
---
""")
        result = discover(str(tmp_path))
        assert len(result.files) == 1
        assert result.files[0].name == "Test Board"
        assert result.files[0].type == "board"

    def test_discover_multiple_brainfiles(self, tmp_path):
        """Test discovering multiple brainfiles."""
        (tmp_path / "brainfile.md").write_text("""---
title: Main
columns: []
---
""")
        (tmp_path / "brainfile.work.md").write_text("""---
title: Work
columns: []
---
""")
        result = discover(str(tmp_path))
        assert len(result.files) == 2

    def test_discover_recursive(self, tmp_path):
        """Test recursive discovery."""
        subdir = tmp_path / "subproject"
        subdir.mkdir()
        (subdir / "brainfile.md").write_text("""---
title: Subproject
columns: []
---
""")
        result = discover(str(tmp_path), DiscoveryOptions(recursive=True))
        assert len(result.files) == 1
        assert "subproject" in result.files[0].relative_path

    def test_discover_non_recursive(self, tmp_path):
        """Test non-recursive discovery."""
        subdir = tmp_path / "subproject"
        subdir.mkdir()
        (subdir / "brainfile.md").write_text("""---
title: Subproject
columns: []
---
""")
        result = discover(str(tmp_path), DiscoveryOptions(recursive=False))
        assert len(result.files) == 0

    def test_discover_excludes_node_modules(self, tmp_path):
        """Test that node_modules is excluded."""
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "brainfile.md").write_text("""---
title: Should be excluded
columns: []
---
""")
        result = discover(str(tmp_path))
        assert len(result.files) == 0

    def test_discover_excludes_git(self, tmp_path):
        """Test that .git is excluded."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "brainfile.md").write_text("""---
title: Should be excluded
columns: []
---
""")
        result = discover(str(tmp_path))
        assert len(result.files) == 0

    def test_discover_hidden_files(self, tmp_path):
        """Test discovering hidden brainfiles."""
        (tmp_path / ".brainfile.md").write_text("""---
title: Hidden
columns: []
---
""")
        result = discover(str(tmp_path), DiscoveryOptions(include_hidden=True))
        assert len(result.files) == 1
        assert result.files[0].is_hidden is True

    def test_discover_exclude_hidden(self, tmp_path):
        """Test excluding hidden brainfiles."""
        (tmp_path / ".brainfile.md").write_text("""---
title: Hidden
columns: []
---
""")
        result = discover(str(tmp_path), DiscoveryOptions(include_hidden=False))
        assert len(result.files) == 0

    def test_discover_counts_tasks(self, tmp_path):
        """Test that task count is calculated."""
        (tmp_path / "brainfile.md").write_text("""---
title: Test
columns:
  - id: todo
    title: To Do
    tasks:
      - id: task-1
        title: Task 1
      - id: task-2
        title: Task 2
---
""")
        result = discover(str(tmp_path))
        assert len(result.files) == 1
        assert result.files[0].item_count == 2
        assert result.total_items == 2


class TestFindPrimaryBrainfile:
    """Tests for find_primary_brainfile."""

    def test_find_brainfile_md(self, tmp_path):
        """Test finding brainfile.md as primary."""
        (tmp_path / "brainfile.md").write_text("""---
title: Primary
columns: []
---
""")
        result = find_primary_brainfile(str(tmp_path))
        assert result is not None
        assert result.name == "Primary"

    def test_priority_order(self, tmp_path):
        """Test priority order of primary brainfile."""
        (tmp_path / ".brainfile.md").write_text("""---
title: Hidden
columns: []
---
""")
        (tmp_path / "brainfile.md").write_text("""---
title: Primary
columns: []
---
""")
        result = find_primary_brainfile(str(tmp_path))
        assert result is not None
        assert result.name == "Primary"  # brainfile.md has priority

    def test_fallback_to_hidden(self, tmp_path):
        """Test fallback to hidden brainfile."""
        (tmp_path / ".brainfile.md").write_text("""---
title: Hidden
columns: []
---
""")
        result = find_primary_brainfile(str(tmp_path))
        assert result is not None
        assert result.name == "Hidden"

    def test_fallback_to_bb(self, tmp_path):
        """Test fallback to .bb.md."""
        (tmp_path / ".bb.md").write_text("""---
title: BB
columns: []
---
""")
        result = find_primary_brainfile(str(tmp_path))
        assert result is not None
        assert result.name == "BB"

    def test_no_brainfile(self, tmp_path):
        """Test when no brainfile exists."""
        result = find_primary_brainfile(str(tmp_path))
        assert result is None


class TestFindNearestBrainfile:
    """Tests for find_nearest_brainfile."""

    def test_find_in_current_dir(self, tmp_path):
        """Test finding brainfile in current directory."""
        (tmp_path / "brainfile.md").write_text("""---
title: Current
columns: []
---
""")
        result = find_nearest_brainfile(str(tmp_path))
        assert result is not None
        assert result.name == "Current"

    def test_find_in_parent_dir(self, tmp_path):
        """Test finding brainfile in parent directory."""
        (tmp_path / "brainfile.md").write_text("""---
title: Parent
columns: []
---
""")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        result = find_nearest_brainfile(str(subdir))
        assert result is not None
        assert result.name == "Parent"

    def test_find_in_grandparent(self, tmp_path):
        """Test finding brainfile in grandparent directory."""
        (tmp_path / "brainfile.md").write_text("""---
title: Grandparent
columns: []
---
""")
        subdir = tmp_path / "subdir" / "nested"
        subdir.mkdir(parents=True)
        result = find_nearest_brainfile(str(subdir))
        assert result is not None
        assert result.name == "Grandparent"

    def test_no_brainfile_found(self, tmp_path):
        """Test when no brainfile is found up the tree."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        result = find_nearest_brainfile(str(subdir))
        # May or may not find one depending on actual filesystem
        # Just ensure it doesn't crash


class TestDiscoveryOptions:
    """Tests for DiscoveryOptions."""

    def test_defaults(self):
        """Test default options."""
        options = DiscoveryOptions()
        assert options.recursive is True
        assert options.include_hidden is True
        assert options.max_depth == 10
        assert options.exclude_dirs is None

    def test_custom_options(self):
        """Test custom options."""
        options = DiscoveryOptions(
            recursive=False,
            include_hidden=False,
            max_depth=5,
            exclude_dirs=["custom_exclude"],
        )
        assert options.recursive is False
        assert options.include_hidden is False
        assert options.max_depth == 5
        assert options.exclude_dirs == ["custom_exclude"]


class TestDiscoveredFile:
    """Tests for DiscoveredFile dataclass."""

    def test_discovered_file(self):
        """Test DiscoveredFile attributes."""
        now = datetime.now()
        file = DiscoveredFile(
            absolute_path="/path/to/brainfile.md",
            relative_path="brainfile.md",
            name="Test Board",
            type="board",
            is_hidden=False,
            is_private=False,
            item_count=5,
            modified_at=now,
        )
        assert file.absolute_path == "/path/to/brainfile.md"
        assert file.relative_path == "brainfile.md"
        assert file.name == "Test Board"
        assert file.type == "board"
        assert file.is_hidden is False
        assert file.is_private is False
        assert file.item_count == 5
        assert file.modified_at == now


class TestDiscoveryResult:
    """Tests for DiscoveryResult dataclass."""

    def test_discovery_result(self):
        """Test DiscoveryResult attributes."""
        now = datetime.now()
        result = DiscoveryResult(
            root="/path/to/project",
            files=[],
            total_items=0,
            discovered_at=now,
        )
        assert result.root == "/path/to/project"
        assert result.files == []
        assert result.total_items == 0
        assert result.discovered_at == now


class TestConstants:
    """Tests for module constants."""

    def test_brainfile_patterns(self):
        """Test BRAINFILE_PATTERNS contains expected patterns."""
        assert "brainfile.md" in BRAINFILE_PATTERNS
        assert ".brainfile.md" in BRAINFILE_PATTERNS
        assert ".bb.md" in BRAINFILE_PATTERNS
        assert "brainfile.*.md" in BRAINFILE_PATTERNS

    def test_brainfile_globs(self):
        """Test BRAINFILE_GLOBS contains expected globs."""
        assert "brainfile.md" in BRAINFILE_GLOBS
        assert "**/brainfile.md" in BRAINFILE_GLOBS

    def test_exclude_dirs(self):
        """Test EXCLUDE_DIRS contains expected directories."""
        assert "node_modules" in EXCLUDE_DIRS
        assert ".git" in EXCLUDE_DIRS
        assert "__pycache__" in EXCLUDE_DIRS
        assert ".venv" in EXCLUDE_DIRS
