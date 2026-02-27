#!/usr/bin/env python3
"""
Sample app demonstrating brainfile-py usage.

This script:
1. Creates a sample brainfile in memory
2. Parses it using the Brainfile class
3. Lists all tasks by column
4. Demonstrates query functions
5. Demonstrates operations (add task, move task)
"""

import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from brainfile import (
    Brainfile,
    Board,
    Column,
    Task,
    Subtask,
    Priority,
    # Query functions
    get_all_tasks,
    get_tasks_by_priority,
    get_tasks_by_tag,
    search_tasks,
    find_task_by_id,
    get_total_task_count,
    # Operations
    add_task,
    move_task,
    patch_task,
    toggle_subtask,
    # Types
    TaskInput,
    TaskPatch,
)


SAMPLE_BRAINFILE = """---
title: My Project Tasks
columns:
  - id: todo
    title: To Do
    tasks:
      - id: task-1
        title: Set up development environment
        description: Install dependencies and configure IDE
        priority: high
        tags:
          - setup
          - dev
        subtasks:
          - id: task-1-1
            title: Install Python 3.11+
            completed: true
          - id: task-1-2
            title: Set up virtual environment
            completed: false
      - id: task-2
        title: Write documentation
        priority: medium
        tags:
          - docs
  - id: in-progress
    title: In Progress
    tasks:
      - id: task-3
        title: Implement core features
        priority: high
        tags:
          - feature
          - core
  - id: done
    title: Done
    tasks:
      - id: task-4
        title: Project setup
        priority: low
        tags:
          - setup
---
"""


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print('=' * 60)


def print_task(task: Task, indent: int = 0) -> None:
    """Print task details."""
    prefix = "  " * indent
    priority_emoji = {
        Priority.LOW: "🟢",
        Priority.MEDIUM: "🟡",
        Priority.HIGH: "🔴",
        Priority.CRITICAL: "⚫",
    }

    p_str = priority_emoji.get(task.priority, "⚪") if task.priority else "⚪"
    print(f"{prefix}{p_str} [{task.id}] {task.title}")

    if task.description:
        print(f"{prefix}   Description: {task.description[:50]}...")
    if task.tags:
        print(f"{prefix}   Tags: {', '.join(task.tags)}")
    if task.subtasks:
        completed = sum(1 for st in task.subtasks if st.completed)
        print(f"{prefix}   Subtasks: {completed}/{len(task.subtasks)} completed")
        for st in task.subtasks:
            check = "✓" if st.completed else "○"
            print(f"{prefix}     [{check}] {st.title}")


def main() -> None:
    print_header("BRAINFILE-PY SAMPLE APP")

    # 1. Parse the brainfile
    print_header("1. PARSING BRAINFILE")
    result = Brainfile.parse_with_errors(SAMPLE_BRAINFILE)

    if result.error:
        print(f"Error: {result.error}")
        return

    if result.warnings:
        for warning in result.warnings:
            print(f"Warning: {warning}")

    board = result.board
    if not board:
        print("Failed to parse board")
        return

    print(f"✓ Parsed board: {board.title}")
    print(f"  Columns: {len(board.columns)}")
    print(f"  Total tasks: {get_total_task_count(board)}")

    # 2. List all tasks by column
    print_header("2. TASKS BY COLUMN")
    for column in board.columns:
        print(f"\n📋 {column.title} ({len(column.tasks)} tasks)")
        print("-" * 40)
        for task in column.tasks:
            print_task(task, indent=1)

    # 3. Query functions demo
    print_header("3. QUERY FUNCTIONS")

    # Get high priority tasks
    high_priority = get_tasks_by_priority(board, Priority.HIGH)
    print(f"\n🔴 High priority tasks ({len(high_priority)}):")
    for task in high_priority:
        print(f"   - {task.title}")

    # Get tasks by tag
    setup_tasks = get_tasks_by_tag(board, "setup")
    print(f"\n🏷️  Tasks tagged 'setup' ({len(setup_tasks)}):")
    for task in setup_tasks:
        print(f"   - {task.title}")

    # Search tasks
    search_results = search_tasks(board, "environment")
    print(f"\n🔍 Search 'environment' ({len(search_results)}):")
    for task in search_results:
        print(f"   - {task.title}")

    # Find specific task
    task_info = find_task_by_id(board, "task-1")
    if task_info:
        print(f"\n📌 Found task-1 in column '{task_info.column.title}' at index {task_info.index}")

    # 4. Operations demo
    print_header("4. OPERATIONS DEMO")

    # Add a new task
    print("\n➕ Adding new task to 'todo' column...")
    result = add_task(
        board,
        "todo",
        TaskInput(
            title="Review pull requests",
            description="Check open PRs and provide feedback",
            priority=Priority.MEDIUM,
            tags=["review", "collaboration"],
        )
    )

    if result.success and result.board:
        board = result.board
        print(f"   ✓ Added task (new total: {get_total_task_count(board)})")
    else:
        print(f"   ✗ Failed: {result.error}")

    # Move a task
    print("\n🔄 Moving task-2 from 'todo' to 'in-progress'...")
    result = move_task(board, "task-2", "todo", "in-progress", 0)

    if result.success and result.board:
        board = result.board
        task_info = find_task_by_id(board, "task-2")
        if task_info:
            print(f"   ✓ Moved to '{task_info.column.title}'")
    else:
        print(f"   ✗ Failed: {result.error}")

    # Patch a task
    print("\n✏️  Updating task-3 priority to critical...")
    result = patch_task(board, "task-3", TaskPatch(priority=Priority.CRITICAL))

    if result.success and result.board:
        board = result.board
        task_info = find_task_by_id(board, "task-3")
        if task_info:
            print(f"   ✓ Updated priority: {task_info.task.priority}")
    else:
        print(f"   ✗ Failed: {result.error}")

    # Toggle subtask
    print("\n☑️  Toggling subtask task-1-2...")
    result = toggle_subtask(board, "task-1", "task-1-2")

    if result.success and result.board:
        board = result.board
        task_info = find_task_by_id(board, "task-1")
        if task_info and task_info.task.subtasks:
            st = next((s for s in task_info.task.subtasks if s.id == "task-1-2"), None)
            if st:
                print(f"   ✓ Subtask completed: {st.completed}")
    else:
        print(f"   ✗ Failed: {result.error}")

    # 5. Serialize back to markdown
    print_header("5. SERIALIZE TO MARKDOWN")
    markdown = Brainfile.serialize(board)
    print(f"Generated {len(markdown)} characters of markdown")
    print("\nFirst 500 characters:")
    print("-" * 40)
    print(markdown[:500])
    print("...")

    # 6. Final state
    print_header("6. FINAL STATE")
    for column in board.columns:
        print(f"\n📋 {column.title} ({len(column.tasks)} tasks)")
        for task in column.tasks:
            p_str = f"[{task.priority.value}]" if task.priority else "[none]"
            print(f"   - {task.id}: {task.title} {p_str}")

    print("\n" + "=" * 60)
    print("  ✅ Sample app completed successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
