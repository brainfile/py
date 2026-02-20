# Brainfile Python Library Port - Research Document

## Executive Summary

This document outlines the research findings for porting the `@brainfile/core` TypeScript library to Python. The port would create a fully-featured Python package (`brainfile-py`) that enables Python projects to parse, manipulate, validate, and serialize Brainfile markdown files.

## Current TypeScript Library Analysis

### Package Overview
- **Name**: `@brainfile/core`
- **Version**: 0.8.0
- **License**: MIT
- **Runtime Dependency**: Only `js-yaml` (YAML parsing)
- **Size**: ~2,500 lines of TypeScript (excluding tests)

### Architecture Overview

```
@brainfile/core/
├── index.ts          # Main entry point, Brainfile class facade
├── types/            # Type definitions
│   ├── base.ts       # Shared types (Task, Subtask, Rule, etc.)
│   ├── board.ts      # Board-specific types (Column, Board)
│   ├── journal.ts    # Journal-specific types
│   └── enums.ts      # BrainfileType, RendererType enums
├── parser.ts         # YAML frontmatter parsing
├── serializer.ts     # Board → Markdown serialization
├── validator.ts      # Schema validation
├── linter.ts         # Syntax checking and auto-fix
├── operations.ts     # Pure mutation functions (immutable)
├── query.ts          # Read-only query functions
├── idGen.ts          # ID generation utilities
├── discovery.ts      # File system discovery
├── templates.ts      # Built-in task templates
├── inference.ts      # Type/renderer inference
├── realtime.ts       # Diffing and hashing
└── schemaHints.ts    # Schema extension parsing
```

### Module Breakdown

#### 1. Types (`types/`)
Core data structures:
- `Task`: id, title, description, priority, tags, assignee, dueDate, subtasks, relatedFiles, template
- `Subtask`: id, title, completed
- `Column`: id, title, order, tasks[]
- `Board`: title, type, columns[], archive[], statsConfig, rules, agent
- `Rule`: id, rule (string)
- `Rules`: always[], never[], prefer[], context[]
- `Journal`, `JournalEntry` (secondary type)

#### 2. Parser (`parser.ts`)
- Extracts YAML frontmatter from markdown
- Handles duplicate column consolidation
- Provides task/rule location finding for editors
- Returns `ParseResult` with data, type, renderer, warnings

#### 3. Serializer (`serializer.ts`)
- Converts Board objects back to markdown with YAML frontmatter
- Configurable: indent, lineWidth, trailingNewline
- Uses js-yaml's `dump()` function

#### 4. Validator (`validator.ts`)
- Validates board structure (columns, tasks, subtasks, rules)
- Returns `ValidationResult` with path-specific errors
- Type-aware validation (board vs journal)

#### 5. Linter (`linter.ts`)
- Checks YAML syntax errors
- Detects unquoted strings with colons (fixable)
- Integrates parser and validator
- Auto-fix capability

#### 6. Operations (`operations.ts`)
**Pure immutable functions** - all return new board objects:
- `moveTask(board, taskId, fromCol, toCol, index)`
- `addTask(board, columnId, input)`
- `updateTask(board, columnId, taskId, title, desc)`
- `deleteTask(board, columnId, taskId)`
- `patchTask(board, taskId, patch)` - partial updates
- `archiveTask(board, columnId, taskId)`
- `restoreTask(board, taskId, toColumnId)`
- Subtask operations: `addSubtask`, `deleteSubtask`, `updateSubtask`, `toggleSubtask`
- Bulk operations: `moveTasks`, `patchTasks`, `deleteTasks`, `archiveTasks`

#### 7. Query (`query.ts`)
**Read-only functions**:
- `findColumnById`, `findColumnByName`
- `findTaskById` - returns task, column, index
- `taskIdExists`, `columnExists`
- `getAllTasks`, `getTasksByTag`, `getTasksByPriority`, `getTasksByAssignee`
- `searchTasks(board, query)` - text search
- `getColumnTaskCount`, `getTotalTaskCount`
- `getTasksWithIncompleteSubtasks`, `getOverdueTasks`

#### 8. ID Generation (`idGen.ts`)
- `generateNextTaskId(board)` → "task-N"
- `generateNextSubtaskId(taskId, existingIds)` → "task-N-M"
- `isValidTaskId`, `isValidSubtaskId`
- `getParentTaskId(subtaskId)`

#### 9. Discovery (`discovery.ts`)
File system utilities (uses Node.js `fs`):
- `discover(rootDir, options)` - find all brainfiles recursively
- `findPrimaryBrainfile(rootDir)` - priority order lookup
- `findNearestBrainfile(startDir)` - walk up directory tree
- `watchBrainfiles(rootDir, callback)` - file watcher

#### 10. Templates (`templates.ts`)
- Built-in templates: bug-report, feature-request, refactor
- `processTemplate(template, values)` - variable substitution
- `getTemplateById`, `getAllTemplateIds`

#### 11. Inference (`inference.ts`)
- `inferType(data, filename)` - detect board/journal/etc.
- `inferRenderer(type, data, schemaHints)` - kanban/timeline/checklist/etc.

#### 12. Realtime (`realtime.ts`)
- `hashBoard(board)` / `hashBoardContent(content)` - SHA-256
- `diffBoards(previous, next)` - structural diff

---

## Python Equivalent Libraries

| TypeScript | Python Equivalent | Notes |
|------------|-------------------|-------|
| `js-yaml` | `PyYAML` or `ruamel.yaml` | ruamel.yaml preserves formatting better |
| `crypto.createHash` | `hashlib` | Standard library |
| `fs` (file system) | `pathlib`, `os` | Standard library |
| TypeScript interfaces | `dataclasses` or `pydantic` | pydantic preferred for validation |
| Jest (testing) | `pytest` | Industry standard |

### Recommended: `pydantic` for Data Models

Pydantic provides:
- Runtime validation (TypeScript only has compile-time)
- JSON Schema generation (for schema.json)
- Serialization/deserialization built-in
- Type coercion
- Clear error messages

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Subtask(BaseModel):
    id: str
    title: str
    completed: bool = False

class Task(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    priority: Optional[Priority] = None
    tags: Optional[List[str]] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = Field(None, alias="dueDate")
    subtasks: Optional[List[Subtask]] = None
    related_files: Optional[List[str]] = Field(None, alias="relatedFiles")

class Column(BaseModel):
    id: str
    title: str
    order: Optional[int] = None
    tasks: List[Task] = []

class Board(BaseModel):
    title: str
    type: Optional[str] = "board"
    columns: List[Column] = []
    archive: Optional[List[Task]] = None
```

### YAML Library Choice: `ruamel.yaml`

Advantages over PyYAML:
- Preserves comments (important for brainfile editing)
- Preserves key ordering
- Better round-trip editing support
- YAML 1.2 support

```python
from ruamel.yaml import YAML

yaml = YAML()
yaml.preserve_quotes = True

# Parse
with open("brainfile.md") as f:
    content = f.read()
    # Extract frontmatter...
    data = yaml.load(yaml_content)

# Serialize
from io import StringIO
stream = StringIO()
yaml.dump(data, stream)
yaml_output = stream.getvalue()
```

---

## Proposed Python API Design

### Main Entry Point

```python
from brainfile import Brainfile, Board, Task

# Parse
board = Brainfile.parse(content)
result = Brainfile.parse_with_errors(content)

# Serialize
markdown = Brainfile.serialize(board)

# Validate
result = Brainfile.validate(board)

# Lint
result = Brainfile.lint(content, auto_fix=True)
```

### Operations (Functional Style)

```python
from brainfile.operations import (
    add_task,
    move_task,
    delete_task,
    patch_task,
    archive_task,
)

# All operations return Result objects with new board
result = add_task(board, "todo", TaskInput(title="New task"))
if result.success:
    board = result.board
else:
    print(result.error)
```

### Query Functions

```python
from brainfile.query import (
    find_task_by_id,
    find_column_by_name,
    get_tasks_by_tag,
    search_tasks,
)

task_info = find_task_by_id(board, "task-1")
if task_info:
    task, column, index = task_info.task, task_info.column, task_info.index
```

### Discovery

```python
from brainfile.discovery import (
    discover,
    find_primary_brainfile,
    find_nearest_brainfile,
)

result = discover("/path/to/project")
for file in result.files:
    print(f"{file.name}: {file.item_count} tasks")
```

---

## Python Package Structure

```
brainfile-py/
├── pyproject.toml        # Modern Python packaging (PEP 517/518)
├── src/
│   └── brainfile/
│       ├── __init__.py   # Main exports
│       ├── models.py     # Pydantic models (Board, Task, etc.)
│       ├── parser.py     # YAML frontmatter parsing
│       ├── serializer.py # Board → Markdown
│       ├── validator.py  # Schema validation
│       ├── linter.py     # Syntax checking
│       ├── operations.py # Pure mutation functions
│       ├── query.py      # Read-only queries
│       ├── id_gen.py     # ID generation
│       ├── discovery.py  # File system discovery
│       ├── templates.py  # Built-in templates
│       ├── inference.py  # Type/renderer inference
│       ├── realtime.py   # Diffing and hashing
│       └── py.typed      # PEP 561 marker
├── tests/
│   ├── test_parser.py
│   ├── test_operations.py
│   ├── test_query.py
│   └── fixtures/
│       └── test_boards.py
└── README.md
```

### pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "brainfile"
version = "0.1.0"
description = "Python library for the Brainfile task management protocol"
readme = "README.md"
license = "MIT"
requires-python = ">=3.9"
authors = [
    { name = "Brainfile Contributors" }
]
keywords = ["brainfile", "task-management", "kanban", "markdown", "yaml"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Typing :: Typed",
]
dependencies = [
    "pydantic>=2.0",
    "ruamel.yaml>=0.18",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "mypy",
    "ruff",
]

[tool.hatch.build.targets.wheel]
packages = ["src/brainfile"]

[tool.mypy]
strict = true
python_version = "3.9"

[tool.ruff]
line-length = 100
target-version = "py39"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

## Implementation Priorities

### Phase 1: Core (MVP)
1. **Models** - Pydantic data classes for Board, Task, Column, etc.
2. **Parser** - YAML frontmatter extraction and parsing
3. **Serializer** - Board → Markdown conversion
4. **Validator** - Basic structure validation

### Phase 2: Operations
5. **Operations** - All mutation functions (add, move, delete, patch)
6. **Query** - All query functions
7. **ID Generation** - Task/subtask ID utilities

### Phase 3: Advanced
8. **Linter** - Syntax checking and auto-fix
9. **Discovery** - File system utilities
10. **Templates** - Built-in templates
11. **Inference** - Type/renderer detection
12. **Realtime** - Diffing and hashing

---

## Key Design Decisions

### 1. Immutable Operations
Like the TypeScript version, all operations should return new board objects rather than mutating in place. This enables:
- Undo/redo functionality
- Predictable state management
- Thread safety

### 2. Result Objects
Operations return `BoardOperationResult` rather than raising exceptions:
```python
@dataclass
class BoardOperationResult:
    success: bool
    board: Optional[Board] = None
    error: Optional[str] = None
```

### 3. Pydantic for Validation
Use Pydantic v2 for:
- Runtime type validation
- JSON Schema generation
- Automatic serialization
- Clear error messages

### 4. Type Hints Throughout
Full typing support for IDE autocomplete and static analysis:
```python
def find_task_by_id(
    board: Board,
    task_id: str
) -> Optional[TaskInfo]:
    ...
```

### 5. Python Naming Conventions
Convert TypeScript camelCase to Python snake_case:
- `addTask` → `add_task`
- `findColumnById` → `find_column_by_id`
- `dueDate` → `due_date` (with Pydantic aliases for YAML compatibility)

---

## Estimated Effort

| Component | TypeScript Lines | Python Estimate | Complexity |
|-----------|------------------|-----------------|------------|
| Models | 150 | 200 | Low |
| Parser | 290 | 200 | Medium |
| Serializer | 75 | 80 | Low |
| Validator | 410 | 350 | Medium |
| Linter | 310 | 280 | Medium |
| Operations | 910 | 800 | Medium |
| Query | 170 | 150 | Low |
| ID Gen | 95 | 80 | Low |
| Discovery | 480 | 400 | Medium |
| Templates | 255 | 220 | Low |
| Inference | 195 | 170 | Low |
| Realtime | 240 | 200 | Medium |
| **Total** | **~2,500** | **~2,900** | - |

**Estimated Development Time**: 2-3 weeks for a complete port with tests.

---

## Testing Strategy

1. **Port existing test fixtures** from TypeScript
2. **Use pytest** with parametrized tests
3. **Property-based testing** with Hypothesis for operations
4. **Coverage target**: 90%+

Example test structure:
```python
# tests/test_operations.py
import pytest
from brainfile import Board
from brainfile.operations import add_task, move_task

class TestAddTask:
    def test_add_task_to_empty_column(self, sample_board):
        result = add_task(sample_board, "todo", {"title": "New task"})
        assert result.success
        assert len(result.board.columns[0].tasks) == 1

    def test_add_task_missing_title_fails(self, sample_board):
        result = add_task(sample_board, "todo", {"title": ""})
        assert not result.success
        assert "title is required" in result.error.lower()
```

---

## Potential Integrations

With a Python port, brainfile can integrate with:

1. **Django/FastAPI** - Web applications with brainfile-backed task management
2. **CLI tools** - `click` or `typer` based command-line interfaces
3. **Jupyter Notebooks** - Interactive task management in notebooks
4. **GitHub Actions** - Python-based CI/CD task tracking
5. **AI/ML pipelines** - Task management for ML experiments
6. **MCP servers** - Python-based Model Context Protocol servers

---

## Open Questions

1. **Comment preservation**: Should we preserve YAML comments during round-trip editing?
   - Recommendation: Yes, use ruamel.yaml for this

2. **Async support**: Should discovery/watch functions be async?
   - Recommendation: Provide both sync and async versions

3. **Compatibility**: Strict compatibility with TypeScript output or Pythonic improvements?
   - Recommendation: Strict compatibility for interoperability

4. **Distribution**: PyPI only or also conda-forge?
   - Recommendation: Start with PyPI, add conda-forge later

---

## Next Steps

1. [ ] Set up project structure with pyproject.toml
2. [ ] Implement Pydantic models
3. [ ] Port parser with ruamel.yaml
4. [ ] Port serializer
5. [ ] Port validator
6. [ ] Port operations (start with add_task, move_task)
7. [ ] Port query functions
8. [ ] Add comprehensive tests
9. [ ] Set up CI/CD (GitHub Actions)
10. [ ] Publish to PyPI
