#!/usr/bin/env python3
"""
Sample app demonstrating brainfile-py v2 usage.

This script:
1. Initializes a workspace with ensure_dirs
2. Creates sample tasks using add_task_file
3. Lists and searches tasks
4. Completes a task (moves to logs/)
"""

import shutil
import sys
import tempfile
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from brainfile import (
    Task,
    ensure_dirs,
    add_task_file,
    list_tasks,
    find_task,
    search_task_files,
    complete_task_file,
    read_tasks_dir,
)


def main() -> None:
    # Create a temporary workspace
    tmp = tempfile.mkdtemp()
    brainfile_path = f"{tmp}/.brainfile/brainfile.md"

    try:
        # 1. Initialize workspace
        dirs = ensure_dirs(brainfile_path)
        print(f"Workspace created at {dirs.dot_dir}")
        print(f"  board_dir: {dirs.board_dir}")
        print(f"  logs_dir:  {dirs.logs_dir}")

        # Write a minimal board config
        Path(dirs.brainfile_path).write_text(
            "---\ntitle: Sample Project\ncolumns:\n"
            "  - id: todo\n    title: To Do\n"
            "  - id: in-progress\n    title: In Progress\n"
            "  - id: done\n    title: Done\n---\n"
        )

        # 2. Add tasks
        print("\nAdding tasks...")
        r1 = add_task_file(dirs.board_dir, {
            "title": "Set up CI pipeline",
            "column": "todo",
            "priority": "high",
            "tags": ["infra", "ci"],
        })
        print(f"  Created {r1['task'].id}: {r1['task'].title}")

        r2 = add_task_file(dirs.board_dir, {
            "title": "Write unit tests",
            "column": "todo",
            "priority": "medium",
            "tags": ["testing"],
        })
        print(f"  Created {r2['task'].id}: {r2['task'].title}")

        r3 = add_task_file(dirs.board_dir, {
            "title": "Deploy to staging",
            "column": "in-progress",
            "priority": "high",
            "tags": ["infra", "deploy"],
        })
        print(f"  Created {r3['task'].id}: {r3['task'].title}")

        # 3. List all tasks
        print("\nAll active tasks:")
        for doc in list_tasks(dirs.board_dir):
            t = doc.task
            prio = f" [{t.priority}]" if t.priority else ""
            tags = f" ({', '.join(t.tags)})" if t.tags else ""
            print(f"  {t.id}: {t.title}{prio}{tags} -> {t.column}")

        # 4. Filter by column
        print("\nTodo tasks:")
        for doc in list_tasks(dirs.board_dir, filters={"column": "todo"}):
            print(f"  {doc.task.id}: {doc.task.title}")

        # 5. Search
        print("\nSearch for 'deploy':")
        for doc in search_task_files(dirs.board_dir, "deploy"):
            print(f"  {doc.task.id}: {doc.task.title}")

        # 6. Find a specific task
        found = find_task(dirs.board_dir, r1["task"].id)
        if found:
            print(f"\nFound task: {found.task.title}")

        # 7. Complete a task
        print(f"\nCompleting {r3['task'].id}...")
        complete_task_file(r3["file_path"], dirs.logs_dir)

        remaining = read_tasks_dir(dirs.board_dir)
        completed = read_tasks_dir(dirs.logs_dir)
        print(f"  Active: {len(remaining)}, Completed: {len(completed)}")

        print("\nDone!")

    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
