# Changelog

## 0.4.2 - 2026-03-08

### Fixed
- reduced implementation complexity in frontmatter, task-file, model coercion, and discovery flows by extracting focused helpers while preserving existing parsing and discovery behavior
- replaced several non-idiomatic patterns with more Pythonic implementations, including `StrEnum` usage, class-based ledger validation, clearer duplicate-column merge handling, and simplified boolean/filter logic
- kept graceful YAML failure behavior intact in task and workspace loading paths after confirming tests depend on broad parse-error handling
- normalized package metadata by keeping the runtime `brainfile.__version__` aligned with the published project version

### Internal
- kept the release-hardening changes narrowly scoped to behavior-preserving cleanup across `frontmatter.py`, `task_file.py`, `models.py`, `discovery.py`, `types_ledger.py`, `parser.py`, `ledger.py`, `task_operations.py`, and `workspace.py`
- validation passed with `uv run pytest`

## 0.4.1 - 2026-03-08

### Fixed
- aligned task and board frontmatter parsing around shared helpers so task files and `.brainfile/brainfile.md` preserve markdown bodies more reliably and report invalid frontmatter consistently
- added workspace helper coverage and documentation for directory resolution, task discovery, body composition, and board-config round trips
- hardened workspace task lookup to search canonical board/log paths first and fall back to scanning renamed task files by task id
- normalized parser duplicate-column handling and location lookup helpers, while simplifying schema-hint and ledger model coercion paths
- corrected package metadata by syncing the runtime `brainfile.__version__` with the released project version

### Internal
- introduced shared frontmatter utilities and small path/coercion refactors across parser, task-file, workspace, discovery, and related model modules
- enforced an 80% pytest coverage floor in project test configuration
