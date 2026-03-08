"""brainfile.files

Filesystem helpers for resolving brainfile paths and ensuring `.brainfile/` state.

This mirrors TS core v2 `utils/files.ts`.

Notes
- Brainfile v2 uses `.brainfile/brainfile.md` as the preferred file.
- Legacy names are also supported: `brainfile.md`, `.brainfile.md`, `.bb.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DOT_BRAINFILE_DIRNAME = ".brainfile"
BRAINFILE_BASENAME = "brainfile.md"
BRAINFILE_STATE_BASENAME = "state.json"  # deprecated
DOT_BRAINFILE_GITIGNORE_BASENAME = ".gitignore"

BrainfileResolutionKind = str  # 'dotdir' | 'root' | 'hidden' | 'bb'


@dataclass(frozen=True)
class FoundBrainfile:
    absolute_path: str
    project_root: str
    kind: BrainfileResolutionKind


def _to_absolute(path: str) -> str:
    return str(Path(path).resolve()) if not Path(path).is_absolute() else path


def _exists_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _brainfile_candidates(current_dir: Path) -> list[tuple[Path, BrainfileResolutionKind]]:
    return [
        (current_dir / DOT_BRAINFILE_DIRNAME / BRAINFILE_BASENAME, "dotdir"),
        (current_dir / BRAINFILE_BASENAME, "root"),
        (current_dir / ".brainfile.md", "hidden"),
        (current_dir / ".bb.md", "bb"),
    ]


def _find_in_directory(current_dir: Path) -> FoundBrainfile | None:
    for path, kind in _brainfile_candidates(current_dir):
        if _exists_file(path):
            return FoundBrainfile(absolute_path=str(path), project_root=str(current_dir), kind=kind)
    return None


def find_brainfile(start_dir: str | None = None) -> FoundBrainfile | None:
    """Walk up from start_dir (or cwd) to find a brainfile.

    Resolution priority per directory:
    1) `.brainfile/brainfile.md` (preferred)
    2) `brainfile.md` (legacy)
    3) `.brainfile.md` (legacy hidden)
    4) `.bb.md` (legacy)
    """

    current_dir = Path(start_dir or Path.cwd()).resolve()

    while True:
        found = _find_in_directory(current_dir)
        if found is not None:
            return found
        if current_dir.parent == current_dir:
            return None
        current_dir = current_dir.parent


@dataclass(frozen=True)
class ResolveBrainfilePathOptions:
    file_path: str | None = None
    start_dir: str | None = None


def resolve_brainfile_path(options: ResolveBrainfilePathOptions | None = None) -> str:
    options = options or ResolveBrainfilePathOptions()
    start_dir = Path(options.start_dir or Path.cwd()).resolve()
    file_path = options.file_path

    is_default_placeholder = file_path is None or file_path in (
        BRAINFILE_BASENAME,
        f"./{BRAINFILE_BASENAME}",
    )

    if is_default_placeholder:
        found = find_brainfile(str(start_dir))
        return found.absolute_path if found else _to_absolute(file_path or BRAINFILE_BASENAME)

    if file_path is None:
        return str(start_dir / BRAINFILE_BASENAME)

    path = Path(file_path)
    if path.is_absolute():
        return str(path)

    return str((start_dir / path).resolve())


def get_brainfile_state_dir(brainfile_path: str) -> str:
    abs_path = Path(_to_absolute(brainfile_path))
    brainfile_dir = abs_path.parent
    if brainfile_dir.name == DOT_BRAINFILE_DIRNAME:
        return str(brainfile_dir)
    return str(brainfile_dir / DOT_BRAINFILE_DIRNAME)


def get_brainfile_state_path(brainfile_path: str) -> str:
    """Deprecated. Brainfile no longer writes/uses state.json."""

    return str(Path(get_brainfile_state_dir(brainfile_path)) / BRAINFILE_STATE_BASENAME)


def get_dot_brainfile_gitignore_path(brainfile_path: str) -> str:
    return str(Path(get_brainfile_state_dir(brainfile_path)) / DOT_BRAINFILE_GITIGNORE_BASENAME)


def ensure_dot_brainfile_dir(brainfile_path: str) -> str:
    directory = Path(get_brainfile_state_dir(brainfile_path))
    directory.mkdir(parents=True, exist_ok=True)
    return str(directory)


def ensure_dot_brainfile_gitignore(brainfile_path: str) -> None:
    ensure_dot_brainfile_dir(brainfile_path)
    gitignore_path = Path(get_dot_brainfile_gitignore_path(brainfile_path))

    if not gitignore_path.exists():
        gitignore_path.write_text("", encoding="utf-8")
