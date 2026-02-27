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
from brainfile import ensureV2Dirs, addTaskFile, readTasksDir, completeTaskFile

# Initialize workspace
dirs = ensureV2Dirs(".brainfile/brainfile.md")

# Add a task
result = addTaskFile(
    dirs.boardDir,
    {"title": "Implement auth", "column": "in-progress", "priority": "high"},
    body="## Description\nAdd JWT authentication to the API.\n",
)
print(result["task"].id)  # "task-1"

# List all active tasks
for doc in readTasksDir(dirs.boardDir):
    t = doc.task
    print(f"{t.id}: {t.title} [{t.column}]")

# Complete a task (moves to logs/)
completeTaskFile(result["filePath"], dirs.logsDir)
```

## Task File Operations

Read and write individual task files.

```python
from brainfile import readTaskFile, writeTaskFile, findV2Task, getV2Dirs

# Read a single task
doc = readTaskFile(".brainfile/board/task-1.md")
print(doc.task.title)
print(doc.body)  # Markdown content below frontmatter

# Find a task across board and logs
dirs = getV2Dirs(".brainfile/brainfile.md")
result = findV2Task(dirs, "task-1", searchLogs=True)
if result:
    print(result["doc"].task.title, "in", "logs" if result["isLog"] else "board")
```

## Contracts

Tasks can carry formal contracts for AI agent coordination: deliverables, validation commands, constraints, and feedback for rework.

```python
from brainfile import readTaskFile, writeTaskFile, Contract, Deliverable

doc = readTaskFile(".brainfile/board/task-1.md")
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

writeTaskFile(".brainfile/board/task-1.md", task, doc.body)
```

### Contract Lifecycle

```
ready  →  in_progress  →  delivered  →  done
                │                         │
                └─────────→  failed  ←────┘
                             (add feedback, reset to ready)
```

```python
from brainfile import setTaskContractStatus

# Agent picks up work
setTaskContractStatus(board, "task-1", "in_progress")

# Agent delivers
setTaskContractStatus(board, "task-1", "delivered")

# PM validates
setTaskContractStatus(board, "task-1", "done")
```

## Board Operations (V1)

Immutable operations on in-memory board objects. Useful for single-file workflows or building custom tools.

```python
from brainfile import Brainfile, add_task, move_task, patch_task, TaskInput, TaskPatch

# Parse a brainfile
result = Brainfile.parse(markdown_content)
board = result.board

# Add a task
result = add_task(board, "todo", TaskInput(title="New task", priority="high"))
board = result.board

# Move between columns
result = move_task(board, "task-1", "todo", "in-progress")

# Patch fields
result = patch_task(board, "task-1", TaskPatch(tags=["urgent"], assignee="codex"))

# Serialize back
output = Brainfile.serialize(board)
```

## Queries

```python
from brainfile import (
    find_task_by_id,
    get_all_tasks,
    get_tasks_by_tag,
    get_tasks_by_assignee,
    search_tasks,
)

task_info = find_task_by_id(board, "task-1")
urgent = get_tasks_by_tag(board, "urgent")
results = search_tasks(board, "auth")
```

## Validation and Linting

```python
from brainfile import BrainfileValidator, BrainfileLinter, LintOptions

# Validate board structure
result = BrainfileValidator.validate(board)
for error in result.errors:
    print(f"{error.path}: {error.message}")

# Lint with auto-fix
result = BrainfileLinter.lint(content, LintOptions(auto_fix=True))
```

## File Discovery

```python
from brainfile import discover, find_nearest_brainfile, isV2

# Find brainfiles in a project
result = discover("/path/to/project")
for f in result.files:
    print(f"{f.name}: {f.item_count} tasks")

# Walk up to find nearest brainfile
path = find_nearest_brainfile()

# Check if a workspace is v2
if isV2(".brainfile/brainfile.md"):
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
