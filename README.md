<p align="center">
  <img src="https://raw.githubusercontent.com/brainfile/core/main/logo.png" alt="Brainfile Logo" width="128" height="128">
</p>

# brainfile

**The Python engine behind [Brainfile](https://brainfile.md).**

This library provides the core logic for managing Brainfile v2 projects: reading/writing task files, managing contracts, validating boards, and querying task state. It is the Python equivalent of [@brainfile/core](https://github.com/brainfile/core) with full API parity.

Used by [Cecli](https://github.com/dwash96/cecli) and other tools that need programmatic access to Brainfile workspaces.

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
└── logs/                 # Completed tasks (history)
    └── task-0.md
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

# Complete a task (moves to logs/)
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

## Development

```bash
git clone https://github.com/brainfile/py.git
cd py
uv sync --dev
uv run pytest
```

## License

MIT
