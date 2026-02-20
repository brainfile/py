"""
Brainfile Discovery Module.

Provides utilities for discovering brainfiles in a workspace/directory.
Used by CLI, editor extensions, and other tools.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from .parser import BrainfileParser


# Patterns for finding brainfiles (in priority order)
BRAINFILE_PATTERNS: tuple[str, ...] = (
    # Standard names
    "brainfile.md",
    ".brainfile.md",
    ".bb.md",
    # Suffixed variants (brainfile.private.md, brainfile.work.md, etc.)
    "brainfile.*.md",
)

# Glob patterns for recursive discovery
BRAINFILE_GLOBS: tuple[str, ...] = (
    # Root level
    "brainfile.md",
    ".brainfile.md",
    ".bb.md",
    "brainfile.*.md",
    # Nested (subfolders)
    "**/brainfile.md",
    "**/.brainfile.md",
    "**/.bb.md",
    "**/brainfile.*.md",
)

# Directories to exclude from discovery
EXCLUDE_DIRS: tuple[str, ...] = (
    "node_modules",
    ".git",
    "dist",
    "build",
    "out",
    ".vscode-test",
    "coverage",
    ".next",
    ".nuxt",
    "vendor",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "venv",
    ".venv",
    "env",
    ".env",
)


@dataclass
class DiscoveredFile:
    """Represents a discovered brainfile."""

    absolute_path: str
    """Absolute path to the file"""

    relative_path: str
    """Path relative to the workspace root"""

    name: str
    """Display name (from board title or filename)"""

    type: str
    """Brainfile type (board, journal, etc.)"""

    is_hidden: bool
    """Whether this is a hidden file (.brainfile.md, .bb.md)"""

    is_private: bool
    """Whether this file appears to be private (contains .private or in .gitignore)"""

    item_count: int
    """Number of items (tasks for boards, entries for journals, etc.)"""

    modified_at: datetime
    """File modification time"""


@dataclass
class DiscoveryOptions:
    """Options for discovery."""

    recursive: bool = True
    """Include nested directories (default: True)"""

    include_hidden: bool = True
    """Include hidden files like .brainfile.md (default: True)"""

    max_depth: int = 10
    """Maximum directory depth for recursive search (default: 10)"""

    exclude_dirs: list[str] | None = None
    """Custom exclude patterns"""


@dataclass
class DiscoveryResult:
    """Result of workspace discovery."""

    root: str
    """Root directory that was searched"""

    files: list[DiscoveredFile] = field(default_factory=list)
    """All discovered brainfiles"""

    total_items: int = 0
    """Total item count across all files"""

    discovered_at: datetime = field(default_factory=datetime.now)
    """Discovery timestamp"""


def is_brainfile_name(filename: str) -> bool:
    """
    Check if a filename matches brainfile patterns.

    Args:
        filename: The filename to check

    Returns:
        True if the filename matches brainfile patterns
    """
    name = os.path.basename(filename).lower()

    # Exact matches
    if name in ("brainfile.md", ".brainfile.md", ".bb.md"):
        return True

    # Suffixed pattern: brainfile.*.md
    if name.startswith("brainfile.") and name.endswith(".md") and name != "brainfile.md":
        return True

    return False


def _should_exclude(file_path: str, exclude_dirs: list[str]) -> bool:
    """Check if a path should be excluded."""
    parts = Path(file_path).parts
    return any(part in exclude_dirs for part in parts)


def extract_brainfile_suffix(filename: str) -> str | None:
    """
    Extract suffix from brainfile name.

    Args:
        filename: The filename to extract suffix from

    Returns:
        The suffix (e.g., "private" from "brainfile.private.md") or None

    Example:
        >>> extract_brainfile_suffix("brainfile.private.md")
        'private'
    """
    name = os.path.basename(filename).lower()

    if name.startswith("brainfile.") and name.endswith(".md") and name != "brainfile.md":
        # Extract middle part: brainfile.SUFFIX.md
        without_prefix = name[len("brainfile.") :]
        suffix = without_prefix[: -len(".md")]
        return suffix if suffix else None

    return None


def _is_private_file(filename: str, relative_path: str) -> bool:
    """Determine if a file is considered private."""
    suffix = extract_brainfile_suffix(filename)

    # Check for private suffix
    if suffix in ("private", "local", "personal"):
        return True

    # Hidden files in hidden directories are often private
    if "/." in relative_path or relative_path.startswith("."):
        return True

    return False


def _count_tasks_from_dict(board: dict) -> int:
    """Count total tasks from a board dict."""
    columns = board.get("columns")
    if not isinstance(columns, list):
        return 0
    total = 0
    for column in columns:
        if isinstance(column, dict):
            tasks = column.get("tasks")
            if isinstance(tasks, list):
                total += len(tasks)
    return total


def _parse_file_metadata(
    absolute_path: str,
    relative_path: str,
) -> DiscoveredFile | None:
    """Parse a brainfile and extract metadata."""
    try:
        with open(absolute_path, encoding="utf-8") as f:
            content = f.read()

        board = BrainfileParser.parse(content)
        stats = os.stat(absolute_path)
        filename = os.path.basename(absolute_path)
        is_hidden = filename.startswith(".")

        if board:
            return DiscoveredFile(
                absolute_path=absolute_path,
                relative_path=relative_path,
                name=board.get("title", filename.replace(".md", "")),
                type=board.get("type", "board"),
                is_hidden=is_hidden,
                is_private=_is_private_file(filename, relative_path),
                item_count=_count_tasks_from_dict(board) if board.get("columns") else 0,
                modified_at=datetime.fromtimestamp(stats.st_mtime),
            )

        # File exists but failed to parse - still include it
        return DiscoveredFile(
            absolute_path=absolute_path,
            relative_path=relative_path,
            name=filename.replace(".md", ""),
            type="unknown",
            is_hidden=is_hidden,
            is_private=_is_private_file(filename, relative_path),
            item_count=0,
            modified_at=datetime.fromtimestamp(stats.st_mtime),
        )

    except Exception:
        return None


def _find_brainfiles_recursive(
    dir_path: str,
    root_dir: str,
    options: DiscoveryOptions,
    current_depth: int = 0,
) -> list[DiscoveredFile]:
    """Recursively find brainfiles in a directory."""
    results: list[DiscoveredFile] = []

    if current_depth > options.max_depth:
        return results

    exclude_dirs = options.exclude_dirs or list(EXCLUDE_DIRS)

    try:
        entries = os.listdir(dir_path)

        for entry in entries:
            full_path = os.path.join(dir_path, entry)
            relative_path = os.path.relpath(full_path, root_dir)

            if os.path.isdir(full_path):
                # Skip excluded directories
                if entry in exclude_dirs:
                    continue

                # Recurse into subdirectories
                if options.recursive:
                    results.extend(
                        _find_brainfiles_recursive(
                            full_path,
                            root_dir,
                            options,
                            current_depth + 1,
                        )
                    )

            elif os.path.isfile(full_path):
                # Check if this is a brainfile
                if not is_brainfile_name(entry):
                    continue

                # Skip hidden files if not included
                if entry.startswith(".") and not options.include_hidden:
                    continue

                metadata = _parse_file_metadata(full_path, relative_path)
                if metadata:
                    results.append(metadata)

    except PermissionError:
        # Directory not readable, skip it
        pass

    return results


def discover(
    root_dir: str,
    options: DiscoveryOptions | None = None,
) -> DiscoveryResult:
    """
    Discover all brainfiles in a workspace directory.

    Args:
        root_dir: The root directory to search
        options: Discovery options

    Returns:
        Discovery result with all found files

    Example:
        >>> result = discover("/path/to/project")
        >>> print(f"Found {len(result.files)} brainfiles")
        >>> for file in result.files:
        ...     print(f"{file.name}: {file.item_count} items")
    """
    if options is None:
        options = DiscoveryOptions()

    if options.exclude_dirs is None:
        options.exclude_dirs = list(EXCLUDE_DIRS)

    absolute_root = os.path.abspath(root_dir)
    files = _find_brainfiles_recursive(absolute_root, absolute_root, options)

    # Sort by path (root files first, then alphabetically)
    files.sort(key=lambda f: (f.relative_path.count(os.sep), f.relative_path))

    return DiscoveryResult(
        root=absolute_root,
        files=files,
        total_items=sum(f.item_count for f in files),
        discovered_at=datetime.now(),
    )


def find_primary_brainfile(root_dir: str) -> DiscoveredFile | None:
    """
    Find the primary brainfile in a directory.

    Returns the first match in priority order: brainfile.md > .brainfile.md > .bb.md

    Args:
        root_dir: The directory to search

    Returns:
        The primary brainfile or None if none found
    """
    absolute_root = os.path.abspath(root_dir)

    # Check in priority order
    priority_names = ["brainfile.md", ".brainfile.md", ".bb.md"]

    for name in priority_names:
        full_path = os.path.join(absolute_root, name)

        if os.path.exists(full_path):
            metadata = _parse_file_metadata(full_path, name)
            if metadata:
                return metadata

    # Fall back to any brainfile.*.md
    try:
        for entry in os.listdir(absolute_root):
            if (
                is_brainfile_name(entry)
                and entry.lower() not in priority_names
                and os.path.isfile(os.path.join(absolute_root, entry))
            ):
                full_path = os.path.join(absolute_root, entry)
                metadata = _parse_file_metadata(full_path, entry)
                if metadata:
                    return metadata

    except PermissionError:
        pass

    return None


def find_nearest_brainfile(start_dir: str | None = None) -> DiscoveredFile | None:
    """
    Find the nearest brainfile by walking up the directory tree.

    Similar to how git finds .git by walking up from cwd.

    Args:
        start_dir: The directory to start searching from (default: current working directory)

    Returns:
        The nearest brainfile or None if none found up to filesystem root

    Example:
        >>> # From /home/user/projects/myapp/src
        >>> # Will find /home/user/projects/myapp/brainfile.md if it exists
        >>> brainfile = find_nearest_brainfile()
        >>> if brainfile:
        ...     print(f"Found: {brainfile.absolute_path}")
    """
    current_dir = os.path.abspath(start_dir or os.getcwd())
    root = os.path.dirname(current_dir)

    # Keep going up until we can't go further
    while True:
        found = find_primary_brainfile(current_dir)
        if found:
            return found

        # Move up to parent directory
        parent_dir = os.path.dirname(current_dir)

        # Safety check: if we can't go up anymore, stop
        if parent_dir == current_dir:
            break

        current_dir = parent_dir

    return None


def watch_brainfiles(
    root_dir: str,
    callback: Callable[[str, DiscoveredFile | str], None],
) -> Callable[[], None]:
    """
    Watch a directory for brainfile changes.

    Uses the watchdog library for cross-platform file watching.

    Args:
        root_dir: The directory to watch
        callback: Called when files change with (event_type, file) where
                  event_type is 'add', 'change', or 'unlink'

    Returns:
        A function to stop watching

    Example:
        >>> def on_change(event, file):
        ...     print(f"{event}: {file}")
        >>> stop = watch_brainfiles("/path/to/project", on_change)
        >>> # Later...
        >>> stop()  # Stop watching
    """
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError as e:
        raise ImportError(
            "watchdog is required for file watching. "
            "Install it with: pip install watchdog"
        ) from e

    absolute_root = os.path.abspath(root_dir)

    class BrainfileHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            filename = os.path.basename(event.src_path)
            if is_brainfile_name(filename):
                relative_path = os.path.relpath(event.src_path, absolute_root)
                metadata = _parse_file_metadata(event.src_path, relative_path)
                if metadata:
                    callback("add", metadata)

        def on_modified(self, event):
            if event.is_directory:
                return
            filename = os.path.basename(event.src_path)
            if is_brainfile_name(filename):
                relative_path = os.path.relpath(event.src_path, absolute_root)
                metadata = _parse_file_metadata(event.src_path, relative_path)
                if metadata:
                    callback("change", metadata)

        def on_deleted(self, event):
            if event.is_directory:
                return
            filename = os.path.basename(event.src_path)
            if is_brainfile_name(filename):
                callback("unlink", event.src_path)

    observer = Observer()
    handler = BrainfileHandler()
    observer.schedule(handler, absolute_root, recursive=True)
    observer.start()

    def stop():
        observer.stop()
        observer.join()

    return stop
