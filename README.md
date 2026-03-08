# brainfile

Python library for the [Brainfile](https://brainfile.md) task coordination protocol. Provides reading/writing task files, managing contracts, validating boards, querying the completion ledger, and full workspace operations. API-equivalent to [@brainfile/core](https://github.com/brainfile/core) (TypeScript).

## Installation

```bash
pip install brainfile
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add brainfile
```

To enable file watching (optional):

```bash
pip install brainfile[watch]
```

## v2 Architecture

Brainfile v2 uses a directory-based structure. Each task is its own markdown file.

```
.brainfile/
├── brainfile.md          # Board config (columns, types, rules)
├── board/                # Active tasks
│   ├── task-1.md
│   └── task-2.md
└── logs/                 # Completion history
    ├── ledger.jsonl      # Unified completion log
    └── task-0.md         # (legacy) Archived task
```

## Quick Start

```python
from brainfile import ensure_dirs, add_task_file, read_tasks_dir, complete_task_file

# Initialize workspace
dirs = ensure_dirs(".brainfile/brainfile.md")

# Add a task
result = add_task_file(
    dirs.board_dir,
    {"title": "Implement auth", "column": "in-progress", "priority": "high"},
    body="## Description\nAdd JWT authentication to the API.\n",
)
print(result["task"].id)  # "task-1"

# List all active tasks
for doc in read_tasks_dir(dirs.board_dir):
    t = doc.task
    print(f"{t.id}: {t.title} [{t.column}]")

# Complete a task (appends to ledger.jsonl, archives to logs/)
complete_task_file(result["file_path"], dirs.logs_dir)
```

## Task File Operations

Read and write individual task files.

```python
from brainfile import read_task_file, write_task_file, find_workspace_task, get_dirs

# Read a single task
doc = read_task_file(".brainfile/board/task-1.md")
print(doc.task.title)
print(doc.body)  # Markdown content below frontmatter

# Find a task across board and logs
dirs = get_dirs(".brainfile/brainfile.md")
result = find_workspace_task(dirs, "task-1", search_logs=True)
if result:
    print(result["doc"].task.title, "in", "logs" if result["is_log"] else "board")
```

## Contracts

Tasks can carry formal contracts for AI agent coordination: deliverables, validation commands, constraints, and feedback for rework.

```python
from brainfile import read_task_file, write_task_file, Contract, Deliverable

doc = read_task_file(".brainfile/board/task-1.md")
task = doc.task

# Attach a contract
task.contract = Contract(
    status="ready",
    deliverables=[
        Deliverable(path="src/auth.py", description="JWT auth module"),
        Deliverable(path="tests/test_auth.py", description="Unit tests"),
    ],
    validation={"commands": ["pytest tests/test_auth.py"]},
    constraints=["Use PyJWT library", "Token expiry must be configurable"],
)

write_task_file(".brainfile/board/task-1.md", task, doc.body)
```

### Contract Lifecycle

```
ready  →  in_progress  →  delivered  →  done
                │                         │
                └─────────→  failed  ←────┘
                             (add feedback, reset to ready)
```

## File Discovery

```python
from brainfile import discover, find_nearest_brainfile, is_workspace

# Find brainfiles in a project
result = discover("/path/to/project")
for f in result.files:
    print(f"{f.name}: {f.item_count} tasks")

# Walk up to find nearest brainfile
path = find_nearest_brainfile()

# Check if a workspace has the v2 board/ directory
if is_workspace(".brainfile/brainfile.md"):
    print("V2 workspace detected")
```

## Ecosystem

| Package | Description |
|---------|-------------|
| [brainfile (Python)](https://github.com/brainfile/py) | This library |
| [@brainfile/core](https://github.com/brainfile/core) | TypeScript core library |
| [@brainfile/cli](https://github.com/brainfile/cli) | CLI with TUI and MCP server |
| [Protocol](https://github.com/brainfile/protocol) | Specification and JSON Schema |

## Workspace Helpers

For multi-agent systems, the workspace helpers provide workspace detection, path resolution, task discovery, task body composition, and board-config parsing.

### Workspace setup and path helpers

Use `get_dirs()` to resolve absolute workspace paths from `.brainfile/brainfile.md`. Use `ensure_dirs()` to create the `board/` and `logs/` directories when bootstrapping a workspace.

```python
from brainfile import ensure_dirs, get_dirs, get_log_file_path, get_task_file_path, is_workspace

brainfile_path = ".brainfile/brainfile.md"

# Resolve canonical absolute paths
resolved = get_dirs(brainfile_path)
print(resolved.dot_dir)
print(resolved.board_dir)
print(resolved.logs_dir)
print(resolved.brainfile_path)

# Create board/ and logs/ if needed
workspace = ensure_dirs(brainfile_path)

# Build canonical task filenames
active_task_path = get_task_file_path(workspace.board_dir, "task-1")
archived_task_path = get_log_file_path(workspace.logs_dir, "task-1")

# Detect whether board/ exists yet
print(is_workspace(brainfile_path))
```

`is_workspace()` currently checks whether the `board/` directory exists for the resolved workspace path. `ensure_dirs()` creates `board/` and `logs/`, but it does not create or validate `.brainfile/brainfile.md` itself.

### Task discovery

Find tasks in the active board and, optionally, archived logs:

```python
from brainfile import find_workspace_task, get_dirs

dirs = get_dirs(".brainfile/brainfile.md")

result = find_workspace_task(dirs, "task-1", search_logs=True)
if result:
    doc = result["doc"]
    print(doc.task.title)
    print(result["file_path"])
    print("archived" if result["is_log"] else "active")
```

The finder checks the canonical `task-N.md` path first, then falls back to scanning markdown files in the directory so renamed task files can still be found by task id. When `search_logs=False`, only the active board is searched.

### Body helpers

Extract or rebuild the standard `Description` and `Log` sections used in task bodies:

```python
from brainfile import compose_body, extract_description, extract_log

body = compose_body(
    description="Implement JWT auth",
    log="- 2026-01-01 started\n- 2026-01-02 in review",
)

print(extract_description(body))
print(extract_log(body))
```

`extract_description()` and `extract_log()` return `None` when the section is missing or empty. `compose_body()` trims each provided section, omits empty sections, and returns an empty string if both values are absent.

### Board config helpers

Parse and serialize `.brainfile/brainfile.md` while preserving markdown body content below the YAML frontmatter:

```python
from brainfile import parse_board_config, read_board_config, serialize_board_config, write_board_config

content = """---
title: My Board
columns:
- id: todo
  title: To Do
---

## Notes
Team guidelines here.
"""

config, body = parse_board_config(content)
serialized = serialize_board_config(config, body)
loaded = read_board_config(".brainfile/brainfile.md")
write_board_config(".brainfile/brainfile.md", config, body)
```

`parse_board_config()` requires YAML frontmatter delimited by `---` lines and returns a `(BoardConfig, body)` tuple. `serialize_board_config()` emits YAML frontmatter and preserves an optional markdown body. `read_board_config()` returns only the parsed `BoardConfig`, while `write_board_config()` writes both config and body back to disk.

## Development

```bash
git clone https://github.com/brainfile/py.git
cd py
uv sync --dev
uv run pytest
```

### Coverage expectations

Pytest is configured in `pyproject.toml` to collect coverage for the `brainfile` package and fail the full suite below **80%** total coverage.

A focused workspace regression suite lives in `tests/test_workspace.py`. It exercises the current workspace helper surface, including:

- `get_dirs()`, `ensure_dirs()`, and `is_workspace()`
- `get_task_file_path()` and `get_log_file_path()`
- `find_workspace_task()` across board files, log files, missing tasks, and renamed task files
- `extract_description()`, `extract_log()`, and `compose_body()`
- `parse_board_config()`, `serialize_board_config()`, `read_board_config()`, and `write_board_config()`

Run the workspace-focused tests with the legacy alias used by the contract:

```bash
uv run pytest tests/test_workspace.py -q
```

Because the repository-wide coverage floor applies to that command too, this focused run still enforces the global **80%** total coverage threshold rather than a per-file threshold for `workspace.py` alone.

Run the full suite with the repository coverage settings:

```bash
uv run pytest
```

## License

MIT
