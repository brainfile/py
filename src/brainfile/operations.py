"""
Pure board mutation operations.

These functions return new board objects without side effects.
All operations are immutable - they create new Board objects rather than
modifying existing ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .id_gen import generate_next_subtask_id, generate_next_task_id
from .models import Board, Column, Priority, Subtask, Task, TemplateType
from .query import find_column_by_id, find_task_by_id


@dataclass
class TaskInput:
    """
    Input for creating a new task.

    Only title is required - all other fields are optional.
    """

    title: str
    description: str | None = None
    priority: Priority | str | None = None
    tags: list[str] | None = None
    assignee: str | None = None
    due_date: str | None = None
    related_files: list[str] | None = None
    template: TemplateType | str | None = None
    subtasks: list[str] | None = None
    """Just titles - IDs are auto-generated"""


@dataclass
class TaskPatch:
    """
    Input for patching an existing task.

    All fields are optional - only provided fields are updated.
    Fields explicitly set to None will be removed from the task.
    Use the special UNSET sentinel to indicate "don't change this field".
    """

    title: str | None = None
    description: str | None | object = field(default_factory=lambda: _UNSET)
    priority: Priority | str | None | object = field(default_factory=lambda: _UNSET)
    tags: list[str] | None | object = field(default_factory=lambda: _UNSET)
    assignee: str | None | object = field(default_factory=lambda: _UNSET)
    due_date: str | None | object = field(default_factory=lambda: _UNSET)
    related_files: list[str] | None | object = field(default_factory=lambda: _UNSET)
    template: TemplateType | str | None | object = field(default_factory=lambda: _UNSET)


class _UnsetType:
    """Sentinel class to distinguish between None (remove) and unset (keep)."""

    def __repr__(self) -> str:
        return "UNSET"


_UNSET = _UnsetType()


@dataclass
class BoardOperationResult:
    """Result of a board operation."""

    success: bool
    board: Board | None = None
    error: str | None = None


@dataclass
class BulkItemResult:
    """Result of a single item in a bulk operation."""

    id: str
    success: bool
    error: str | None = None


@dataclass
class BulkOperationResult:
    """Result of a bulk operation."""

    success: bool
    board: Board | None = None
    results: list[BulkItemResult] = field(default_factory=list)
    success_count: int = 0
    """Number of successfully processed items"""
    failure_count: int = 0
    """Number of failed items"""


def _deep_copy_board(board: Board) -> Board:
    """
    Create a deep copy of a board for immutable operations.

    All board operations are immutable - they create new Board objects
    rather than modifying existing ones. This function creates a complete
    deep copy of the board including all columns, tasks, subtasks, and
    other nested structures.

    Args:
        board: The source board to copy

    Returns:
        A new Board instance that is completely independent of the original.
        Modifications to the copy will not affect the original.
    """
    return board.model_copy(deep=True)


def move_task(
    board: Board,
    task_id: str,
    from_column_id: str,
    to_column_id: str,
    to_index: int,
) -> BoardOperationResult:
    """
    Move a task from one column to another at a specific index.

    Args:
        board: Board to modify
        task_id: ID of task to move
        from_column_id: Source column ID
        to_column_id: Target column ID
        to_index: Index in target column

    Returns:
        BoardOperationResult with new board or error
    """
    from_column = find_column_by_id(board, from_column_id)
    if not from_column:
        return BoardOperationResult(
            success=False,
            error=f"Source column {from_column_id} not found",
        )

    to_column = find_column_by_id(board, to_column_id)
    if not to_column:
        return BoardOperationResult(
            success=False,
            error=f"Target column {to_column_id} not found",
        )

    # Find task in source column
    task_index = -1
    task: Task | None = None
    for i, t in enumerate(from_column.tasks):
        if t.id == task_id:
            task_index = i
            task = t
            break

    if task_index == -1 or task is None:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} not found in column {from_column_id}",
        )

    # Create new board with task moved
    new_board = _deep_copy_board(board)

    for col in new_board.columns:
        if col.id == from_column_id and col.id == to_column_id:
            # Same column - reorder
            tasks = list(col.tasks)
            moved_task = tasks.pop(task_index)
            tasks.insert(to_index, moved_task)
            col.tasks = tasks
        elif col.id == from_column_id:
            # Remove from source
            col.tasks = [t for t in col.tasks if t.id != task_id]
        elif col.id == to_column_id:
            # Add to target
            tasks = list(col.tasks)
            # Create a copy of the task for the new column
            task_copy = task.model_copy(deep=True)
            tasks.insert(to_index, task_copy)
            col.tasks = tasks

    return BoardOperationResult(success=True, board=new_board)


def add_task(
    board: Board,
    column_id: str,
    input_data: TaskInput,
) -> BoardOperationResult:
    """
    Add a new task to a column.

    Args:
        board: Board to modify
        column_id: Target column ID
        input_data: Task input (title required, all other fields optional)

    Returns:
        BoardOperationResult with new board or error
    """
    column = find_column_by_id(board, column_id)
    if not column:
        return BoardOperationResult(
            success=False,
            error=f"Column {column_id} not found",
        )

    if not input_data.title or input_data.title.strip() == "":
        return BoardOperationResult(
            success=False,
            error="Task title is required",
        )

    new_task_id = generate_next_task_id(board)

    # Generate subtasks with auto-generated IDs
    subtasks: list[Subtask] | None = None
    if input_data.subtasks:
        subtasks = [
            Subtask(
                id=f"{new_task_id}-{index + 1}",
                title=title.strip(),
                completed=False,
            )
            for index, title in enumerate(input_data.subtasks)
        ]

    # Convert priority string to enum if needed
    priority: Priority | None = None
    if input_data.priority:
        if isinstance(input_data.priority, Priority):
            priority = input_data.priority
        else:
            try:
                priority = Priority(input_data.priority)
            except ValueError:
                pass

    # Convert template string to enum if needed
    template: TemplateType | None = None
    if input_data.template:
        if isinstance(input_data.template, TemplateType):
            template = input_data.template
        else:
            try:
                template = TemplateType(input_data.template)
            except ValueError:
                pass

    new_task = Task(
        id=new_task_id,
        title=input_data.title.strip(),
        description=input_data.description.strip() if input_data.description else None,
        priority=priority,
        tags=input_data.tags if input_data.tags and len(input_data.tags) > 0 else None,
        assignee=input_data.assignee,
        due_date=input_data.due_date,
        related_files=(
            input_data.related_files
            if input_data.related_files and len(input_data.related_files) > 0
            else None
        ),
        template=template,
        subtasks=subtasks if subtasks and len(subtasks) > 0 else None,
    )

    # Create new board with added task
    new_board = _deep_copy_board(board)

    for col in new_board.columns:
        if col.id == column_id:
            col.tasks = list(col.tasks) + [new_task]
            break

    return BoardOperationResult(success=True, board=new_board)


def update_task(
    board: Board,
    column_id: str,
    task_id: str,
    new_title: str,
    new_description: str,
) -> BoardOperationResult:
    """
    Update a task's title and description.

    Args:
        board: Board to modify
        column_id: Column ID containing the task
        task_id: Task ID to update
        new_title: New task title
        new_description: New task description

    Returns:
        BoardOperationResult with new board or error
    """
    column = find_column_by_id(board, column_id)
    if not column:
        return BoardOperationResult(
            success=False,
            error=f"Column {column_id} not found",
        )

    task_found = any(t.id == task_id for t in column.tasks)
    if not task_found:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} not found in column {column_id}",
        )

    # Create new board with updated task
    new_board = _deep_copy_board(board)

    for col in new_board.columns:
        if col.id == column_id:
            for task in col.tasks:
                if task.id == task_id:
                    task.title = new_title
                    task.description = new_description
                    break
            break

    return BoardOperationResult(success=True, board=new_board)


def delete_task(
    board: Board,
    column_id: str,
    task_id: str,
) -> BoardOperationResult:
    """
    Delete a task from a column.

    Args:
        board: Board to modify
        column_id: Column ID containing the task
        task_id: Task ID to delete

    Returns:
        BoardOperationResult with new board or error
    """
    column = find_column_by_id(board, column_id)
    if not column:
        return BoardOperationResult(
            success=False,
            error=f"Column {column_id} not found",
        )

    task_exists = any(t.id == task_id for t in column.tasks)
    if not task_exists:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} not found in column {column_id}",
        )

    # Create new board with task removed
    new_board = _deep_copy_board(board)

    for col in new_board.columns:
        if col.id == column_id:
            col.tasks = [t for t in col.tasks if t.id != task_id]
            break

    return BoardOperationResult(success=True, board=new_board)


def toggle_subtask(
    board: Board,
    task_id: str,
    subtask_id: str,
) -> BoardOperationResult:
    """
    Toggle a subtask's completed status.

    Args:
        board: Board to modify
        task_id: Parent task ID
        subtask_id: Subtask ID to toggle

    Returns:
        BoardOperationResult with new board or error
    """
    task_info = find_task_by_id(board, task_id)
    if not task_info:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} not found",
        )

    task = task_info.task
    column = task_info.column

    if not task.subtasks or len(task.subtasks) == 0:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} has no subtasks",
        )

    subtask_found = any(st.id == subtask_id for st in task.subtasks)
    if not subtask_found:
        return BoardOperationResult(
            success=False,
            error=f"Subtask {subtask_id} not found",
        )

    # Create new board with toggled subtask
    new_board = _deep_copy_board(board)

    for col in new_board.columns:
        if col.id == column.id:
            for t in col.tasks:
                if t.id == task_id and t.subtasks:
                    for st in t.subtasks:
                        if st.id == subtask_id:
                            st.completed = not st.completed
                            break
                    break
            break

    return BoardOperationResult(success=True, board=new_board)


def update_board_title(board: Board, new_title: str) -> BoardOperationResult:
    """
    Update board title.

    Args:
        board: Board to modify
        new_title: New board title

    Returns:
        BoardOperationResult with new board
    """
    new_board = _deep_copy_board(board)
    new_board.title = new_title
    return BoardOperationResult(success=True, board=new_board)


def update_stats_config(board: Board, columns: list[str]) -> BoardOperationResult:
    """
    Update stats configuration.

    Args:
        board: Board to modify
        columns: List of column IDs to display in stats

    Returns:
        BoardOperationResult with new board
    """
    from .models import StatsConfig

    new_board = _deep_copy_board(board)
    new_board.stats_config = StatsConfig(columns=columns)
    return BoardOperationResult(success=True, board=new_board)


def archive_task(
    board: Board,
    column_id: str,
    task_id: str,
) -> BoardOperationResult:
    """
    Archive a task (move from column to archive).

    Args:
        board: Board to modify
        column_id: Column ID containing the task
        task_id: Task ID to archive

    Returns:
        BoardOperationResult with new board or error
    """
    column = find_column_by_id(board, column_id)
    if not column:
        return BoardOperationResult(
            success=False,
            error=f"Column {column_id} not found",
        )

    task: Task | None = None
    for t in column.tasks:
        if t.id == task_id:
            task = t
            break

    if not task:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} not found in column {column_id}",
        )

    # Create new board with task archived
    new_board = _deep_copy_board(board)

    # Remove from column
    for col in new_board.columns:
        if col.id == column_id:
            col.tasks = [t for t in col.tasks if t.id != task_id]
            break

    # Add to archive
    task_copy = task.model_copy(deep=True)
    if new_board.archive is None:
        new_board.archive = []
    new_board.archive = list(new_board.archive) + [task_copy]

    return BoardOperationResult(success=True, board=new_board)


def restore_task(
    board: Board,
    task_id: str,
    to_column_id: str,
) -> BoardOperationResult:
    """
    Restore a task from archive to a column.

    Args:
        board: Board to modify
        task_id: Task ID to restore
        to_column_id: Target column ID

    Returns:
        BoardOperationResult with new board or error
    """
    if not board.archive or len(board.archive) == 0:
        return BoardOperationResult(
            success=False,
            error="Archive is empty",
        )

    task: Task | None = None
    for t in board.archive:
        if t.id == task_id:
            task = t
            break

    if not task:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} not found in archive",
        )

    to_column = find_column_by_id(board, to_column_id)
    if not to_column:
        return BoardOperationResult(
            success=False,
            error=f"Target column {to_column_id} not found",
        )

    # Create new board with task restored
    new_board = _deep_copy_board(board)

    # Add to column
    task_copy = task.model_copy(deep=True)
    for col in new_board.columns:
        if col.id == to_column_id:
            col.tasks = list(col.tasks) + [task_copy]
            break

    # Remove from archive
    new_board.archive = [t for t in new_board.archive if t.id != task_id] if new_board.archive else []

    return BoardOperationResult(success=True, board=new_board)


def patch_task(
    board: Board,
    task_id: str,
    patch: TaskPatch,
) -> BoardOperationResult:
    """
    Patch a task with partial updates.

    Only provided fields are updated - unset fields are unchanged.
    Fields set to None are removed from the task.

    Args:
        board: Board to modify
        task_id: Task ID to patch (searches all columns)
        patch: Partial task updates

    Returns:
        BoardOperationResult with new board or error
    """
    task_info = find_task_by_id(board, task_id)
    if not task_info:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} not found",
        )

    column = task_info.column

    # Create new board with patched task
    new_board = _deep_copy_board(board)

    for col in new_board.columns:
        if col.id == column.id:
            for task in col.tasks:
                if task.id == task_id:
                    # Apply patch
                    if patch.title is not None:
                        task.title = patch.title.strip()

                    if not isinstance(patch.description, _UnsetType):
                        if patch.description is None:
                            task.description = None
                        else:
                            task.description = patch.description.strip()

                    if not isinstance(patch.priority, _UnsetType):
                        if patch.priority is None:
                            task.priority = None
                        elif isinstance(patch.priority, Priority):
                            task.priority = patch.priority
                        else:
                            try:
                                task.priority = Priority(patch.priority)
                            except ValueError:
                                task.priority = None

                    if not isinstance(patch.tags, _UnsetType):
                        if patch.tags is None or (isinstance(patch.tags, list) and len(patch.tags) == 0):
                            task.tags = None
                        else:
                            task.tags = patch.tags

                    if not isinstance(patch.assignee, _UnsetType):
                        task.assignee = patch.assignee

                    if not isinstance(patch.due_date, _UnsetType):
                        task.due_date = patch.due_date

                    if not isinstance(patch.related_files, _UnsetType):
                        if patch.related_files is None or (
                            isinstance(patch.related_files, list) and len(patch.related_files) == 0
                        ):
                            task.related_files = None
                        else:
                            task.related_files = patch.related_files

                    if not isinstance(patch.template, _UnsetType):
                        if patch.template is None:
                            task.template = None
                        elif isinstance(patch.template, TemplateType):
                            task.template = patch.template
                        else:
                            try:
                                task.template = TemplateType(patch.template)
                            except ValueError:
                                task.template = None

                    break
            break

    return BoardOperationResult(success=True, board=new_board)


def add_subtask(
    board: Board,
    task_id: str,
    title: str,
) -> BoardOperationResult:
    """
    Add a subtask to a task.

    Args:
        board: Board to modify
        task_id: Parent task ID
        title: Subtask title

    Returns:
        BoardOperationResult with new board or error
    """
    task_info = find_task_by_id(board, task_id)
    if not task_info:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} not found",
        )

    if not title or title.strip() == "":
        return BoardOperationResult(
            success=False,
            error="Subtask title is required",
        )

    task = task_info.task
    column = task_info.column
    existing_ids = [st.id for st in task.subtasks] if task.subtasks else []
    new_subtask_id = generate_next_subtask_id(task_id, existing_ids)

    new_subtask = Subtask(
        id=new_subtask_id,
        title=title.strip(),
        completed=False,
    )

    # Create new board with added subtask
    new_board = _deep_copy_board(board)

    for col in new_board.columns:
        if col.id == column.id:
            for t in col.tasks:
                if t.id == task_id:
                    if t.subtasks is None:
                        t.subtasks = []
                    t.subtasks = list(t.subtasks) + [new_subtask]
                    break
            break

    return BoardOperationResult(success=True, board=new_board)


def delete_subtask(
    board: Board,
    task_id: str,
    subtask_id: str,
) -> BoardOperationResult:
    """
    Delete a subtask from a task.

    Args:
        board: Board to modify
        task_id: Parent task ID
        subtask_id: Subtask ID to delete

    Returns:
        BoardOperationResult with new board or error
    """
    task_info = find_task_by_id(board, task_id)
    if not task_info:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} not found",
        )

    task = task_info.task
    column = task_info.column

    if not task.subtasks or len(task.subtasks) == 0:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} has no subtasks",
        )

    subtask_exists = any(st.id == subtask_id for st in task.subtasks)
    if not subtask_exists:
        return BoardOperationResult(
            success=False,
            error=f"Subtask {subtask_id} not found",
        )

    # Create new board with deleted subtask
    new_board = _deep_copy_board(board)

    for col in new_board.columns:
        if col.id == column.id:
            for t in col.tasks:
                if t.id == task_id and t.subtasks:
                    remaining = [st for st in t.subtasks if st.id != subtask_id]
                    t.subtasks = remaining if remaining else None
                    break
            break

    return BoardOperationResult(success=True, board=new_board)


def update_subtask(
    board: Board,
    task_id: str,
    subtask_id: str,
    title: str,
) -> BoardOperationResult:
    """
    Update a subtask's title.

    Args:
        board: Board to modify
        task_id: Parent task ID
        subtask_id: Subtask ID to update
        title: New subtask title

    Returns:
        BoardOperationResult with new board or error
    """
    task_info = find_task_by_id(board, task_id)
    if not task_info:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} not found",
        )

    if not title or title.strip() == "":
        return BoardOperationResult(
            success=False,
            error="Subtask title is required",
        )

    task = task_info.task
    column = task_info.column

    if not task.subtasks or len(task.subtasks) == 0:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} has no subtasks",
        )

    subtask_exists = any(st.id == subtask_id for st in task.subtasks)
    if not subtask_exists:
        return BoardOperationResult(
            success=False,
            error=f"Subtask {subtask_id} not found",
        )

    # Create new board with updated subtask
    new_board = _deep_copy_board(board)

    for col in new_board.columns:
        if col.id == column.id:
            for t in col.tasks:
                if t.id == task_id and t.subtasks:
                    for st in t.subtasks:
                        if st.id == subtask_id:
                            st.title = title.strip()
                            break
                    break
            break

    return BoardOperationResult(success=True, board=new_board)


def set_subtasks_completed(
    board: Board,
    task_id: str,
    subtask_ids: list[str],
    completed: bool,
) -> BoardOperationResult:
    """
    Set multiple subtasks to completed or incomplete.

    Args:
        board: Board to modify
        task_id: Parent task ID
        subtask_ids: Array of subtask IDs to update
        completed: Whether to mark as completed (True) or incomplete (False)

    Returns:
        BoardOperationResult with new board or error
    """
    task_info = find_task_by_id(board, task_id)
    if not task_info:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} not found",
        )

    task = task_info.task
    column = task_info.column

    if not task.subtasks or len(task.subtasks) == 0:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} has no subtasks",
        )

    # Validate all subtask IDs exist before making changes (atomic)
    existing_ids = {st.id for st in task.subtasks}
    for subtask_id in subtask_ids:
        if subtask_id not in existing_ids:
            return BoardOperationResult(
                success=False,
                error=f"Subtask {subtask_id} not found",
            )

    subtask_id_set = set(subtask_ids)

    # Create new board with updated subtasks
    new_board = _deep_copy_board(board)

    for col in new_board.columns:
        if col.id == column.id:
            for t in col.tasks:
                if t.id == task_id and t.subtasks:
                    for st in t.subtasks:
                        if st.id in subtask_id_set:
                            st.completed = completed
                    break
            break

    return BoardOperationResult(success=True, board=new_board)


def set_all_subtasks_completed(
    board: Board,
    task_id: str,
    completed: bool,
) -> BoardOperationResult:
    """
    Set all subtasks in a task to completed or incomplete.

    Args:
        board: Board to modify
        task_id: Parent task ID
        completed: Whether to mark as completed (True) or incomplete (False)

    Returns:
        BoardOperationResult with new board or error
    """
    task_info = find_task_by_id(board, task_id)
    if not task_info:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} not found",
        )

    task = task_info.task
    column = task_info.column

    if not task.subtasks or len(task.subtasks) == 0:
        return BoardOperationResult(
            success=False,
            error=f"Task {task_id} has no subtasks",
        )

    # Create new board with all subtasks updated
    new_board = _deep_copy_board(board)

    for col in new_board.columns:
        if col.id == column.id:
            for t in col.tasks:
                if t.id == task_id and t.subtasks:
                    for st in t.subtasks:
                        st.completed = completed
                    break
            break

    return BoardOperationResult(success=True, board=new_board)


# =============================================================================
# BULK OPERATIONS
# =============================================================================


def move_tasks(
    board: Board,
    task_ids: list[str],
    to_column_id: str,
) -> BulkOperationResult:
    """
    Move multiple tasks to a target column.

    Operations are applied sequentially - partial success is possible.

    Args:
        board: Board to modify
        task_ids: Array of task IDs to move
        to_column_id: Target column ID

    Returns:
        BulkOperationResult with results for each task
    """
    results: list[BulkItemResult] = []
    current_board = board

    # Validate target column exists first
    to_column = find_column_by_id(board, to_column_id)
    if not to_column:
        return BulkOperationResult(
            success=False,
            results=[
                BulkItemResult(
                    id=task_id,
                    success=False,
                    error=f"Target column {to_column_id} not found",
                )
                for task_id in task_ids
            ],
            success_count=0,
            failure_count=len(task_ids),
        )

    for task_id in task_ids:
        task_info = find_task_by_id(current_board, task_id)
        if not task_info:
            results.append(
                BulkItemResult(
                    id=task_id,
                    success=False,
                    error=f"Task {task_id} not found",
                )
            )
            continue

        # Skip if already in target column
        if task_info.column.id == to_column_id:
            results.append(BulkItemResult(id=task_id, success=True))
            continue

        target_column = find_column_by_id(current_board, to_column_id)
        to_index = len(target_column.tasks) if target_column else 0

        result = move_task(
            current_board,
            task_id,
            task_info.column.id,
            to_column_id,
            to_index,
        )
        if result.success and result.board:
            current_board = result.board
            results.append(BulkItemResult(id=task_id, success=True))
        else:
            results.append(
                BulkItemResult(
                    id=task_id,
                    success=False,
                    error=result.error,
                )
            )

    success_count = sum(1 for r in results if r.success)
    failure_count = sum(1 for r in results if not r.success)

    return BulkOperationResult(
        success=failure_count == 0,
        board=current_board,
        results=results,
        success_count=success_count,
        failure_count=failure_count,
    )


def patch_tasks(
    board: Board,
    task_ids: list[str],
    patch: TaskPatch,
) -> BulkOperationResult:
    """
    Apply a patch to multiple tasks.

    Operations are applied sequentially - partial success is possible.

    Args:
        board: Board to modify
        task_ids: Array of task IDs to patch
        patch: Patch to apply to all tasks

    Returns:
        BulkOperationResult with results for each task
    """
    results: list[BulkItemResult] = []
    current_board = board

    for task_id in task_ids:
        result = patch_task(current_board, task_id, patch)
        if result.success and result.board:
            current_board = result.board
            results.append(BulkItemResult(id=task_id, success=True))
        else:
            results.append(
                BulkItemResult(
                    id=task_id,
                    success=False,
                    error=result.error,
                )
            )

    success_count = sum(1 for r in results if r.success)
    failure_count = sum(1 for r in results if not r.success)

    return BulkOperationResult(
        success=failure_count == 0,
        board=current_board,
        results=results,
        success_count=success_count,
        failure_count=failure_count,
    )


def delete_tasks(
    board: Board,
    task_ids: list[str],
) -> BulkOperationResult:
    """
    Delete multiple tasks.

    Operations are applied sequentially - partial success is possible.

    Args:
        board: Board to modify
        task_ids: Array of task IDs to delete (searches all columns)

    Returns:
        BulkOperationResult with results for each task
    """
    results: list[BulkItemResult] = []
    current_board = board

    for task_id in task_ids:
        task_info = find_task_by_id(current_board, task_id)
        if not task_info:
            results.append(
                BulkItemResult(
                    id=task_id,
                    success=False,
                    error=f"Task {task_id} not found",
                )
            )
            continue

        result = delete_task(current_board, task_info.column.id, task_id)
        if result.success and result.board:
            current_board = result.board
            results.append(BulkItemResult(id=task_id, success=True))
        else:
            results.append(
                BulkItemResult(
                    id=task_id,
                    success=False,
                    error=result.error,
                )
            )

    success_count = sum(1 for r in results if r.success)
    failure_count = sum(1 for r in results if not r.success)

    return BulkOperationResult(
        success=failure_count == 0,
        board=current_board,
        results=results,
        success_count=success_count,
        failure_count=failure_count,
    )


def archive_tasks(
    board: Board,
    task_ids: list[str],
) -> BulkOperationResult:
    """
    Archive multiple tasks.

    Operations are applied sequentially - partial success is possible.

    Args:
        board: Board to modify
        task_ids: Array of task IDs to archive (searches all columns)

    Returns:
        BulkOperationResult with results for each task
    """
    results: list[BulkItemResult] = []
    current_board = board

    for task_id in task_ids:
        task_info = find_task_by_id(current_board, task_id)
        if not task_info:
            results.append(
                BulkItemResult(
                    id=task_id,
                    success=False,
                    error=f"Task {task_id} not found",
                )
            )
            continue

        result = archive_task(current_board, task_info.column.id, task_id)
        if result.success and result.board:
            current_board = result.board
            results.append(BulkItemResult(id=task_id, success=True))
        else:
            results.append(
                BulkItemResult(
                    id=task_id,
                    success=False,
                    error=result.error,
                )
            )

    success_count = sum(1 for r in results if r.success)
    failure_count = sum(1 for r in results if not r.success)

    return BulkOperationResult(
        success=failure_count == 0,
        board=current_board,
        results=results,
        success_count=success_count,
        failure_count=failure_count,
    )
