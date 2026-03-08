from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from .parser import BrainfileParser

__all__ = [
    "BRAINFILE_PATTERNS",
    "BRAINFILE_GLOBS",
    "EXCLUDE_DIRS",
    "DiscoveredFile",
    "DiscoveryOptions",
    "DiscoveryResult",
    "WatchError",
    "WatchResult",
    "discover",
    "extract_brainfile_suffix",
    "find_nearest_brainfile",
    "find_primary_brainfile",
    "is_brainfile_name",
    "watch_brainfiles",
]

BRAINFILE_PATTERNS = ("brainfile.md", ".brainfile.md", ".bb.md", "brainfile.*.md")
BRAINFILE_GLOBS = (
    "brainfile.md",
    ".brainfile.md",
    ".bb.md",
    "brainfile.*.md",
    "**/brainfile.md",
    "**/.brainfile.md",
    "**/.bb.md",
    "**/brainfile.*.md",
)
EXCLUDE_DIRS = (
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
    absolute_path: str
    relative_path: str
    name: str
    type: str
    is_hidden: bool
    is_private: bool
    item_count: int
    modified_at: datetime


@dataclass
class DiscoveryOptions:
    recursive: bool = True
    include_hidden: bool = True
    max_depth: int = 10
    exclude_dirs: list[str] | None = None


@dataclass
class DiscoveryResult:
    root: str
    files: list[DiscoveredFile] = field(default_factory=list)
    total_items: int = 0
    discovered_at: datetime = field(default_factory=datetime.now)


@dataclass
class WatchError:
    code: str
    message: str
    path: str


@dataclass
class WatchResult:
    success: bool
    stop: Callable[[], None]
    is_active: Callable[[], bool]
    error: WatchError | None = None


def is_brainfile_name(filename: str) -> bool:
    name = os.path.basename(filename).lower()
    return name in {"brainfile.md", ".brainfile.md", ".bb.md"} or (
        name.startswith("brainfile.") and name.endswith(".md") and name != "brainfile.md"
    )


def extract_brainfile_suffix(filename: str) -> str | None:
    name = os.path.basename(filename).lower()
    if name.startswith("brainfile.") and name.endswith(".md") and name != "brainfile.md":
        return name[len("brainfile.") : -3] or None
    return None


def _is_private_file(filename: str, relative_path: str) -> bool:
    return (
        extract_brainfile_suffix(filename) in {"private", "local", "personal"}
        or "/." in relative_path
        or relative_path.startswith(".")
    )


def _count_tasks_from_dict(board: dict) -> int:
    columns = board.get("columns")
    if not isinstance(columns, list):
        return 0
    return sum(
        len(tasks)
        for column in columns
        if isinstance(column, dict)
        for tasks in [column.get("tasks")]
        if isinstance(tasks, list)
    )


def _parse_file_metadata(path: str, relative_path: str) -> DiscoveredFile | None:
    try:
        board = BrainfileParser.parse(Path(path).read_text(encoding="utf-8"))
        name = os.path.basename(path)
        board_data = board or {}
        title = board_data.get("title")
        file_type = board_data.get("type")

        return DiscoveredFile(
            absolute_path=path,
            relative_path=relative_path,
            name=title if isinstance(title, str) and title else name.removesuffix(".md"),
            type=file_type if isinstance(file_type, str) and file_type else ("board" if board else "unknown"),
            is_hidden=name.startswith("."),
            is_private=_is_private_file(name, relative_path),
            item_count=_count_tasks_from_dict(board) if isinstance(board, dict) else 0,
            modified_at=datetime.fromtimestamp(os.stat(path).st_mtime),
        )
    except Exception:
        return None


def _effective_exclude_dirs(options: DiscoveryOptions) -> list[str]:
    return list(options.exclude_dirs) if options.exclude_dirs is not None else list(EXCLUDE_DIRS)


def _should_recurse(entry_name: str, options: DiscoveryOptions, exclude_dirs: list[str]) -> bool:
    return options.recursive and entry_name not in exclude_dirs


def _should_include_file(entry_name: str, options: DiscoveryOptions) -> bool:
    return is_brainfile_name(entry_name) and (options.include_hidden or not entry_name.startswith("."))


def _find(
    dir_path: str,
    root: str,
    options: DiscoveryOptions,
    exclude_dirs: list[str],
    depth: int = 0,
) -> list[DiscoveredFile]:
    if depth > options.max_depth:
        return []

    discovered: list[DiscoveredFile] = []
    try:
        entries = os.listdir(dir_path)
    except PermissionError:
        return discovered

    for entry_name in entries:
        path = os.path.join(dir_path, entry_name)
        relative_path = os.path.relpath(path, root)

        if os.path.isdir(path):
            if _should_recurse(entry_name, options, exclude_dirs):
                discovered.extend(_find(path, root, options, exclude_dirs, depth + 1))
            continue

        if not os.path.isfile(path) or not _should_include_file(entry_name, options):
            continue

        metadata = _parse_file_metadata(path, relative_path)
        if metadata is not None:
            discovered.append(metadata)

    return discovered


def discover(root_dir: str, options: DiscoveryOptions | None = None) -> DiscoveryResult:
    resolved_options = options or DiscoveryOptions()
    exclude_dirs = _effective_exclude_dirs(resolved_options)
    root = os.path.abspath(root_dir)
    files = _find(root, root, resolved_options, exclude_dirs)
    files.sort(key=lambda file: (file.relative_path.count(os.sep), file.relative_path))
    return DiscoveryResult(root, files, sum(file.item_count for file in files), datetime.now())


def find_primary_brainfile(root_dir: str) -> DiscoveredFile | None:
    root = os.path.abspath(root_dir)

    for name in ("brainfile.md", ".brainfile.md", ".bb.md"):
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        metadata = _parse_file_metadata(path, name)
        if metadata is not None:
            return metadata

    try:
        entries = os.listdir(root)
    except PermissionError:
        return None

    for entry_name in entries:
        path = os.path.join(root, entry_name)
        if (
            is_brainfile_name(entry_name)
            and entry_name.lower() not in {"brainfile.md", ".brainfile.md", ".bb.md"}
            and os.path.isfile(path)
        ):
            metadata = _parse_file_metadata(path, entry_name)
            if metadata is not None:
                return metadata

    return None


def find_nearest_brainfile(start_dir: str | None = None) -> DiscoveredFile | None:
    current = os.path.abspath(start_dir or os.getcwd())
    while True:
        found = find_primary_brainfile(current)
        if found is not None:
            return found

        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def watch_brainfiles(
    root_dir: str,
    callback: Callable[[str, DiscoveredFile | str], None],
    on_error: Callable[[WatchError], None] | None = None,
) -> WatchResult:
    root = os.path.abspath(root_dir)

    def fail(code: str, message: str) -> WatchResult:
        return WatchResult(False, lambda: None, lambda: False, WatchError(code, message, root))

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        return fail("UNKNOWN", "watchdog is required for file watching. Install it with: pip install watchdog")

    if not os.path.isdir(root):
        if os.path.exists(root):
            return fail("ENOTDIR", f"Path is not a directory: {root}")
        return fail("ENOENT", f"Directory does not exist: {root}")

    try:
        os.listdir(root)
    except PermissionError:
        return fail("EACCES", f"Permission denied: {root}")

    active = False
    lock = threading.RLock()
    observer: Observer | None = None
    current_observer: Observer | None = None

    def is_active() -> bool:
        with lock:
            return active

    def report(code: str, message: str, path: str) -> None:
        if on_error is None:
            return
        try:
            on_error(WatchError(code, message, path))
        except Exception:
            pass

    class Handler(FileSystemEventHandler):
        def _handle(self, event, kind: str) -> None:
            if event.is_directory or not is_active():
                return
            if not is_brainfile_name(os.path.basename(event.src_path)):
                return

            try:
                if kind == "unlink":
                    callback("unlink", event.src_path)
                    return

                metadata = _parse_file_metadata(event.src_path, os.path.relpath(event.src_path, root))
                if metadata is not None:
                    callback(kind, metadata)
            except OSError as err:
                report("UNKNOWN", f"Error processing file event: {err}", event.src_path)
            except Exception as err:
                report("UNKNOWN", f"Error processing file event: {err}", event.src_path)

        def on_created(self, event) -> None:
            self._handle(event, "add")

        def on_modified(self, event) -> None:
            self._handle(event, "change")

        def on_deleted(self, event) -> None:
            self._handle(event, "unlink")

    try:
        observer = Observer()
        observer.schedule(Handler(), root, recursive=True)
        observer.start()
    except Exception as err:
        return fail("UNKNOWN", f"Failed to watch directory: {err}")

    with lock:
        active = True

    def stop() -> None:
        nonlocal active, observer
        with lock:
            if not active:
                return
            active = False
            current_observer = observer
            observer = None

        if current_observer is None:
            return

        try:
            current_observer.stop()
            if current_observer.is_alive() and threading.current_thread() is not current_observer:
                current_observer.join()
        except Exception:
            pass

    return WatchResult(True, stop, is_active)
