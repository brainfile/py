"""brainfile.files

Filesystem helpers for resolving brainfile paths and ensuring `.brainfile/` state.

This mirrors TS core v2 `utils/files.ts`.

Notes
- Brainfile v2 uses `.brainfile/brainfile.md` as the preferred file.
- Legacy names are also supported: `brainfile.md`, `.brainfile.md`, `.bb.md`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

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


def _to_absolute(p: str) -> str:
    return p if os.path.isabs(p) else os.path.abspath(p)


def _exists_file(p: str) -> bool:
    try:
        return os.path.isfile(p)
    except Exception:
        return False


def find_brainfile(start_dir: str | None = None) -> FoundBrainfile | None:
    """Walk up from start_dir (or cwd) to find a brainfile.

    Resolution priority per directory:
    1) `.brainfile/brainfile.md` (preferred)
    2) `brainfile.md` (legacy)
    3) `.brainfile.md` (legacy hidden)
    4) `.bb.md` (legacy)
    """

    current_dir = os.path.abspath(start_dir or os.getcwd())
    root = os.path.abspath(os.sep)

    while True:
        preferred = os.path.join(current_dir, DOT_BRAINFILE_DIRNAME, BRAINFILE_BASENAME)
        if _exists_file(preferred):
            return FoundBrainfile(absolute_path=preferred, project_root=current_dir, kind="dotdir")

        legacy = os.path.join(current_dir, BRAINFILE_BASENAME)
        if _exists_file(legacy):
            return FoundBrainfile(absolute_path=legacy, project_root=current_dir, kind="root")

        hidden_legacy = os.path.join(current_dir, ".brainfile.md")
        if _exists_file(hidden_legacy):
            return FoundBrainfile(
                absolute_path=hidden_legacy, project_root=current_dir, kind="hidden"
            )

        bb_legacy = os.path.join(current_dir, ".bb.md")
        if _exists_file(bb_legacy):
            return FoundBrainfile(absolute_path=bb_legacy, project_root=current_dir, kind="bb")

        if current_dir == root:
            break

        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent

    return None


@dataclass(frozen=True)
class ResolveBrainfilePathOptions:
    file_path: str | None = None
    start_dir: str | None = None


def resolve_brainfile_path(options: ResolveBrainfilePathOptions | None = None) -> str:
    options = options or ResolveBrainfilePathOptions()
    start_dir = os.path.abspath(options.start_dir or os.getcwd())
    file_path = options.file_path

    is_default_placeholder = file_path is None or file_path in (
        BRAINFILE_BASENAME,
        f"./{BRAINFILE_BASENAME}",
    )

    if is_default_placeholder:
        found = find_brainfile(start_dir)
        if found:
            return found.absolute_path
        return _to_absolute(file_path or BRAINFILE_BASENAME)

    if os.path.isabs(file_path):
        return file_path

    return os.path.abspath(os.path.join(start_dir, file_path))


def get_brainfile_state_dir(brainfile_path: str) -> str:
    abs_path = _to_absolute(brainfile_path)
    brainfile_dir = os.path.dirname(abs_path)
    if os.path.basename(brainfile_dir) == DOT_BRAINFILE_DIRNAME:
        return brainfile_dir
    return os.path.join(brainfile_dir, DOT_BRAINFILE_DIRNAME)


def get_brainfile_state_path(brainfile_path: str) -> str:
    """Deprecated. Brainfile no longer writes/uses state.json."""

    return os.path.join(get_brainfile_state_dir(brainfile_path), BRAINFILE_STATE_BASENAME)


def get_dot_brainfile_gitignore_path(brainfile_path: str) -> str:
    return os.path.join(get_brainfile_state_dir(brainfile_path), DOT_BRAINFILE_GITIGNORE_BASENAME)


def ensure_dot_brainfile_dir(brainfile_path: str) -> str:
    d = get_brainfile_state_dir(brainfile_path)
    os.makedirs(d, exist_ok=True)
    return d


def ensure_dot_brainfile_gitignore(brainfile_path: str) -> None:
    ensure_dot_brainfile_dir(brainfile_path)
    gitignore_path = get_dot_brainfile_gitignore_path(brainfile_path)

    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("")
