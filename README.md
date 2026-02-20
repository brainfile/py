# brainfile

Python port of the @brainfile/core TypeScript library for parsing, manipulating, and serializing brainfile.md kanban boards.

## Installation

```bash
pip install brainfile
```

## Features

- Parse and serialize brainfile.md YAML frontmatter
- Full Pydantic v2 data models with type safety
- Immutable board operations (add, update, delete, move tasks)
- Query functions for searching and filtering
- Board diffing and hashing for real-time sync
- File discovery and watching
- Linting with auto-fix capabilities
- Built-in task templates

## Quick Start

```python
from brainfile import Brainfile

# Parse a brainfile
content = """---
title: My Project
columns:
  - id: todo
    title: To Do
    tasks:
      - id: task-1
        title: First task
---
"""

result = Brainfile.parse(content)
board = result.board

# Add a task
from brainfile import add_task, TaskInput

result = add_task(board, "todo", TaskInput(title="New task"))
updated_board = result.board

# Serialize back to markdown
markdown = Brainfile.serialize(updated_board)
```

## API Reference

### Parsing

```python
from brainfile import BrainfileParser

# Parse to dict
data = BrainfileParser.parse(content)

# Parse to Board model with error handling
result = BrainfileParser.parse_with_errors(content)
if result.error:
    print(f"Error: {result.error}")
else:
    board = result.board
```

### Operations

All operations are immutable and return a new board:

```python
from brainfile import (
    add_task,
    update_task,
    delete_task,
    move_task,
    patch_task,
    archive_task,
    restore_task,
    TaskInput,
    TaskPatch,
)

# Add a task
result = add_task(board, "column-id", TaskInput(title="New task"))

# Update a task
result = update_task(board, "column-id", "task-id", "New Title", "New Description")

# Move a task
result = move_task(board, "task-id", "from-column", "to-column", position=0)

# Patch specific fields
result = patch_task(board, "task-id", TaskPatch(priority="high", tags=["urgent"]))
```

### Queries

```python
from brainfile import (
    find_task_by_id,
    get_all_tasks,
    get_tasks_by_tag,
    get_tasks_by_priority,
    search_tasks,
)

# Find a specific task
task_info = find_task_by_id(board, "task-1")

# Get all tasks with a tag
tasks = get_tasks_by_tag(board, "urgent")

# Search tasks by text
tasks = search_tasks(board, "bug fix")
```

### Validation and Linting

```python
from brainfile import BrainfileValidator, BrainfileLinter, LintOptions

# Validate a board
result = BrainfileValidator.validate(board)
if not result.valid:
    for error in result.errors:
        print(f"{error.path}: {error.message}")

# Lint content with auto-fix
result = BrainfileLinter.lint(content, LintOptions(auto_fix=True))
if result.fixed_content:
    print("Fixed content:", result.fixed_content)
```

### File Discovery

```python
from brainfile import discover, find_nearest_brainfile

# Discover all brainfiles in a directory
result = discover("/path/to/project")
for file in result.files:
    print(f"{file.name}: {file.item_count} tasks")

# Find nearest brainfile (walks up directory tree)
brainfile = find_nearest_brainfile()
```

## License

MIT
