"""brainfile.files

Filesystem helpers for resolving brainfile paths and ensuring `.brainfile/` state.

This mirrors TS core v2 `utils/files.ts`.

Notes
- Brainfile v2 uses `.brainfile/brainfile.md` as the preferred file.
- Legacy names are also supported: `brainfile.md`, `.brainfile.md`, `.bb.md`.
"""

from __future__ import annotations

# ruff: noqa: N802,N803
import os
from dataclasses import dataclass

DOT_BRAINFILE_DIRNAME = ".brainfile"
BRAINFILE_BASENAME = "brainfile.md"
BRAINFILE_STATE_BASENAME = "state.json"  # deprecated
DOT_BRAINFILE_GITIGNORE_BASENAME = ".gitignore"

BrainfileResolutionKind = str  # 'dotdir' | 'root' | 'hidden' | 'bb'


@dataclass(frozen=True)
class FoundBrainfile:
    absolutePath: str
    projectRoot: str
    kind: BrainfileResolutionKind


def _to_absolute(p: str) -> str:
    return p if os.path.isabs(p) else os.path.abspath(p)


def _exists_file(p: str) -> bool:
    try:
        return os.path.isfile(p)
    except Exception:
        return False


def findBrainfile(startDir: str | None = None) -> FoundBrainfile | None:
    """Walk up from startDir (or cwd) to find a brainfile.

    Resolution priority per directory:
    1) `.brainfile/brainfile.md` (preferred)
    2) `brainfile.md` (legacy)
    3) `.brainfile.md` (legacy hidden)
    4) `.bb.md` (legacy)
    """

    current_dir = os.path.abspath(startDir or os.getcwd())
    root = os.path.abspath(os.sep)

    while True:
        preferred = os.path.join(current_dir, DOT_BRAINFILE_DIRNAME, BRAINFILE_BASENAME)
        if _exists_file(preferred):
            return FoundBrainfile(absolutePath=preferred, projectRoot=current_dir, kind="dotdir")

        legacy = os.path.join(current_dir, BRAINFILE_BASENAME)
        if _exists_file(legacy):
            return FoundBrainfile(absolutePath=legacy, projectRoot=current_dir, kind="root")

        hidden_legacy = os.path.join(current_dir, ".brainfile.md")
        if _exists_file(hidden_legacy):
            return FoundBrainfile(absolutePath=hidden_legacy, projectRoot=current_dir, kind="hidden")

        bb_legacy = os.path.join(current_dir, ".bb.md")
        if _exists_file(bb_legacy):
            return FoundBrainfile(absolutePath=bb_legacy, projectRoot=current_dir, kind="bb")

        if current_dir == root:
            break

        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent

    return None


@dataclass(frozen=True)
class ResolveBrainfilePathOptions:
    filePath: str | None = None
    startDir: str | None = None


def resolveBrainfilePath(options: ResolveBrainfilePathOptions | None = None) -> str:
    options = options or ResolveBrainfilePathOptions()
    start_dir = os.path.abspath(options.startDir or os.getcwd())
    file_path = options.filePath

    is_default_placeholder = file_path is None or file_path in (
        BRAINFILE_BASENAME,
        f"./{BRAINFILE_BASENAME}",
    )

    if is_default_placeholder:
        found = findBrainfile(start_dir)
        if found:
            return found.absolutePath
        return _to_absolute(file_path or BRAINFILE_BASENAME)

    if os.path.isabs(file_path):
        return file_path

    return os.path.abspath(os.path.join(start_dir, file_path))


def getBrainfileStateDir(brainfilePath: str) -> str:
    abs_path = _to_absolute(brainfilePath)
    brainfile_dir = os.path.dirname(abs_path)
    if os.path.basename(brainfile_dir) == DOT_BRAINFILE_DIRNAME:
        return brainfile_dir
    return os.path.join(brainfile_dir, DOT_BRAINFILE_DIRNAME)


def getBrainfileStatePath(brainfilePath: str) -> str:
    """Deprecated. Brainfile no longer writes/uses state.json."""

    return os.path.join(getBrainfileStateDir(brainfilePath), BRAINFILE_STATE_BASENAME)


def getDotBrainfileGitignorePath(brainfilePath: str) -> str:
    return os.path.join(getBrainfileStateDir(brainfilePath), DOT_BRAINFILE_GITIGNORE_BASENAME)


def ensureDotBrainfileDir(brainfilePath: str) -> str:
    d = getBrainfileStateDir(brainfilePath)
    os.makedirs(d, exist_ok=True)
    return d


def ensureDotBrainfileGitignore(brainfilePath: str) -> None:
    ensureDotBrainfileDir(brainfilePath)
    gitignore_path = getDotBrainfileGitignorePath(brainfilePath)

    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("")
