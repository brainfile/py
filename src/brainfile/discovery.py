from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol, TypeAlias

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

PathLike: TypeAlias = str | Path


class _WatchdogEvent(Protocol):
    src_path: str
    is_directory: bool


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
    name = Path(filename).name.lower()
    return name in {"brainfile.md", ".brainfile.md", ".bb.md"} or (
        name.startswith("brainfile.") and name.endswith(".md") and name != "brainfile.md"
    )


def extract_brainfile_suffix(filename: str) -> str | None:
    name = Path(filename).name.lower()
    if name.startswith("brainfile.") and name.endswith(".md") and name != "brainfile.md":
        return name[len("brainfile.") : -3] or None
    return None


def _is_private_file(filename: str, relative_path: str) -> bool:
    relative = Path(relative_path)
    return (
        extract_brainfile_suffix(filename) in {"private", "local", "personal"}
        or any(part.startswith(".") for part in relative.parts)
    )


def _count_tasks_from_dict(board: dict[str, object]) -> int:
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


def _coerce_discovered_name(path: Path, title: object) -> str:
    if isinstance(title, str) and title:
        return title
    return path.stem


def _coerce_discovered_type(board: dict[str, object] | None) -> str:
    if not board:
        return "unknown"
    file_type = board.get("type")
    if isinstance(file_type, str) and file_type:
        return file_type
    return "board"


def _parse_file_metadata(path: Path, root: Path) -> DiscoveredFile | None:
    try:
        board = BrainfileParser.parse(path.read_text(encoding="utf-8"))
        board_data = board if isinstance(board, dict) else None
        relative_path = path.relative_to(root).as_posix()

        return DiscoveredFile(
            absolute_path=str(path),
            relative_path=relative_path,
            name=_coerce_discovered_name(path, board_data.get("title") if board_data else None),
            type=_coerce_discovered_type(board_data),
            is_hidden=path.name.startswith("."),
            is_private=_is_private_file(path.name, relative_path),
            item_count=_count_tasks_from_dict(board_data) if board_data is not None else 0,
            modified_at=datetime.fromtimestamp(path.stat().st_mtime),
        )
    except OSError:
        return None


def _effective_exclude_dirs(options: DiscoveryOptions) -> list[str]:
    return list(options.exclude_dirs) if options.exclude_dirs is not None else list(EXCLUDE_DIRS)


def _should_recurse(entry_name: str, options: DiscoveryOptions, exclude_dirs: list[str]) -> bool:
    return options.recursive and entry_name not in exclude_dirs


def _should_include_file(entry_name: str, options: DiscoveryOptions) -> bool:
    return is_brainfile_name(entry_name) and (options.include_hidden or not entry_name.startswith("."))


def _iter_directory_entries(dir_path: Path) -> list[Path]:
    try:
        return list(dir_path.iterdir())
    except PermissionError:
        return []


def _discover_directory(entry: Path, root: Path, options: DiscoveryOptions, exclude_dirs: list[str], depth: int) -> list[DiscoveredFile]:
    if not _should_recurse(entry.name, options, exclude_dirs):
        return []
    return _find(entry, root, options, exclude_dirs, depth + 1)


def _discover_file(entry: Path, root: Path, options: DiscoveryOptions) -> DiscoveredFile | None:
    if not entry.is_file() or not _should_include_file(entry.name, options):
        return None
    return _parse_file_metadata(entry, root)


def _iter_discovered_entries(
    dir_path: Path,
    root: Path,
    options: DiscoveryOptions,
    exclude_dirs: list[str],
    depth: int,
) -> list[DiscoveredFile]:
    discovered: list[DiscoveredFile] = []
    for entry in _iter_directory_entries(dir_path):
        if entry.is_dir():
            discovered.extend(_discover_directory(entry, root, options, exclude_dirs, depth))
            continue

        metadata = _discover_file(entry, root, options)
        if metadata is not None:
            discovered.append(metadata)
    return discovered


def _find(
    dir_path: Path,
    root: Path,
    options: DiscoveryOptions,
    exclude_dirs: list[str],
    depth: int = 0,
) -> list[DiscoveredFile]:
    if depth > options.max_depth:
        return []
    return _iter_discovered_entries(dir_path, root, options, exclude_dirs, depth)


def discover(root_dir: str, options: DiscoveryOptions | None = None) -> DiscoveryResult:
    resolved_options = options or DiscoveryOptions()
    exclude_dirs = _effective_exclude_dirs(resolved_options)
    root = Path(root_dir).resolve()
    files = _find(root, root, resolved_options, exclude_dirs)
    files.sort(key=lambda file: (file.relative_path.count("/"), file.relative_path))
    return DiscoveryResult(str(root), files, sum(file.item_count for file in files), datetime.now())


def _primary_candidate_names() -> tuple[str, ...]:
    return ("brainfile.md", ".brainfile.md", ".bb.md")


def _find_primary_known_file(root: Path) -> DiscoveredFile | None:
    for name in _primary_candidate_names():
        metadata = _parse_primary_candidate(root, name)
        if metadata is not None:
            return metadata
    return None


def _parse_primary_candidate(root: Path, name: str) -> DiscoveredFile | None:
    path = root / name
    if not path.exists():
        return None
    return _parse_file_metadata(path, root)


def _find_primary_suffixed_file(root: Path) -> DiscoveredFile | None:
    for entry in _iter_directory_entries(root):
        if not _is_suffixed_brainfile_entry(entry):
            continue

        metadata = _parse_file_metadata(entry, root)
        if metadata is not None:
            return metadata

    return None


def _is_suffixed_brainfile_entry(entry: Path) -> bool:
    if not is_brainfile_name(entry.name):
        return False
    if entry.name.lower() in {"brainfile.md", ".brainfile.md", ".bb.md"}:
        return False
    return entry.is_file()


def find_primary_brainfile(root_dir: str) -> DiscoveredFile | None:
    root = Path(root_dir).resolve()
    return _find_primary_known_file(root) or _find_primary_suffixed_file(root)


def find_nearest_brainfile(start_dir: str | None = None) -> DiscoveredFile | None:
    current = Path(start_dir or Path.cwd()).resolve()
    while True:
        found = find_primary_brainfile(str(current))
        if found is not None:
            return found

        parent = current.parent
        if parent == current:
            return None
        current = parent


def watch_brainfiles(
    root_dir: str,
    callback: Callable[[str, DiscoveredFile | str], None],
    on_error: Callable[[WatchError], None] | None = None,
) -> WatchResult:
    root = Path(root_dir).resolve()

    def fail(code: str, message: str) -> WatchResult:
        return WatchResult(False, lambda: None, lambda: False, WatchError(code, message, str(root)))

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        return fail("UNKNOWN", "watchdog is required for file watching. Install it with: pip install watchdog")

    startup_error = _validate_watch_root(root)
    if startup_error is not None:
        return fail(*startup_error)

    state = {"active": False}
    lock = threading.RLock()
    observer: Observer | None = None

    def is_active() -> bool:
        with lock:
            return state["active"]

    def report(code: str, message: str, path: str) -> None:
        if on_error is None:
            return
        try:
            on_error(WatchError(code, message, path))
        except (TypeError, ValueError, RuntimeError):
            pass

    def _handle_callback_event(event: _WatchdogEvent, kind: str) -> None:
        event_path = Path(event.src_path)
        if _should_skip_watch_event(event, event_path, is_active):
            return

        try:
            event_payload = _build_watch_event_payload(kind, event_path, root)
            if event_payload is not None:
                callback(kind, event_payload)
        except OSError as err:
            report("UNKNOWN", f"Error processing file event: {err}", str(event_path))

    class Handler(FileSystemEventHandler):
        def on_created(self, event: _WatchdogEvent) -> None:
            _handle_callback_event(event, "add")

        def on_modified(self, event: _WatchdogEvent) -> None:
            _handle_callback_event(event, "change")

        def on_deleted(self, event: _WatchdogEvent) -> None:
            _handle_callback_event(event, "unlink")

    try:
        observer = Observer()
        observer.schedule(Handler(), str(root), recursive=True)
        observer.start()
    except (OSError, RuntimeError) as err:
        return fail("UNKNOWN", f"Failed to watch directory: {err}")

    with lock:
        state["active"] = True

    def stop() -> None:
        nonlocal observer
        with lock:
            if not state["active"]:
                return
            state["active"] = False
            current_observer = observer
            observer = None

        if current_observer is None:
            return

        try:
            current_observer.stop()
            if current_observer.is_alive() and threading.current_thread() is not current_observer:
                current_observer.join()
        except (RuntimeError, OSError):
            pass

    return WatchResult(True, stop, is_active)


def _validate_watch_root(root: Path) -> tuple[str, str] | None:
    if root.is_dir():
        try:
            list(root.iterdir())
        except PermissionError:
            return "EACCES", f"Permission denied: {root}"
        return None

    if root.exists():
        return "ENOTDIR", f"Path is not a directory: {root}"

    return "ENOENT", f"Directory does not exist: {root}"


def _should_skip_watch_event(
    event: _WatchdogEvent,
    event_path: Path,
    is_active: Callable[[], bool],
) -> bool:
    return event.is_directory or not is_active() or not is_brainfile_name(event_path.name)


def _build_watch_event_payload(
    kind: str,
    event_path: Path,
    root: Path,
) -> DiscoveredFile | str | None:
    if kind == "unlink":
        return str(event_path)
    return _parse_file_metadata(event_path, root)
