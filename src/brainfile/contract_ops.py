"""brainfile.contract_ops

Contract operations for PM-to-agent workflows.

These are pure board mutation operations, following the same patterns as
``operations.py``: no side effects, no in-place mutation, and returning a
``BoardOperationResult``.

This mirrors TS core v2 ``contract.ts``.
"""

from __future__ import annotations

# ruff: noqa: N802,N803,N815
from typing import Callable, TypedDict

from .models import (
    Board,
    Contract,
    ContractContext,
    ContractStatus,
    Deliverable,
    Task,
    ValidationConfig,
)
from .operations import BoardOperationResult
from .query import find_task_by_id


class ContractPatch(TypedDict, total=False):
    """
    Patch input for updating an existing task contract.

    - ``None`` fields in this TypedDict are treated as "remove the field" 
      when the field is optional in the model.
    """

    status: ContractStatus
    deliverables: list[Deliverable] | None
    validation: ValidationConfig | None
    constraints: list[str] | None
    context: ContractContext | None


class TaskUpdate(TypedDict, total=False):
    ok: bool
    task: Task | None
    error: str | None


def _update_task_by_id(
    board: Board,
    taskId: str,
    updater: Callable[[Task], TaskUpdate],
) -> BoardOperationResult:
    task_info = find_task_by_id(board, taskId)
    if not task_info:
        return BoardOperationResult(success=False, error=f"Task {taskId} not found")

    column = task_info.column
    updated = updater(task_info.task)
    if not updated.get("ok"):
        return BoardOperationResult(success=False, error=updated.get("error"))

    updated_task = updated.get("task")
    if not updated_task:
        return BoardOperationResult(success=False, error="Updater returned no task")

    new_board = board.model_copy(deep=True)
    for col in new_board.columns:
        if col.id != column.id:
            continue
        col.tasks = [
            updated_task if t.id == taskId else t for t in col.tasks
        ]

    return BoardOperationResult(success=True, board=new_board)


def _get_contract(task: Task) -> dict:
    if not task.contract:
        return {"ok": False, "error": f"Task {task.id} has no contract"}
    return {"ok": True, "contract": task.contract}


def _normalize_non_empty(input_str: str, error_message: str) -> dict:
    trimmed = input_str.strip()
    if not trimmed:
        return {"ok": False, "error": error_message}
    return {"ok": True, "value": trimmed}


def setTaskContract(
    board: Board, taskId: str, contract: Contract
) -> BoardOperationResult:
    """Set (create or replace) the contract on a task."""
    return _update_task_by_id(
        board, taskId, lambda task: {"ok": True, "task": task.model_copy(update={"contract": contract})}
    )


def clearTaskContract(board: Board, taskId: str) -> BoardOperationResult:
    """Remove a contract from a task."""

    def updater(task: Task) -> TaskUpdate:
        if not task.contract:
            return {"ok": False, "error": f"Task {task.id} has no contract"}
        new_task = task.model_copy(update={"contract": None})
        return {"ok": True, "task": new_task}

    return _update_task_by_id(board, taskId, updater)


def setTaskContractStatus(
    board: Board, taskId: str, status: ContractStatus
) -> BoardOperationResult:
    """Update only the contract status."""

    def updater(task: Task) -> TaskUpdate:
        res = _get_contract(task)
        if not res["ok"]:
            return {"ok": False, "error": res["error"]}
        contract = res["contract"].model_copy(update={"status": status})
        return {"ok": True, "task": task.model_copy(update={"contract": contract})}

    return _update_task_by_id(board, taskId, updater)


def patchTaskContract(
    board: Board, taskId: str, patch: ContractPatch
) -> BoardOperationResult:
    """Patch a task's existing contract."""

    def updater(task: Task) -> TaskUpdate:
        res = _get_contract(task)
        if not res["ok"]:
            return {"ok": False, "error": res["error"]}

        contract = res["contract"].model_copy(deep=True)

        if "status" in patch:
            contract.status = patch["status"]

        if "deliverables" in patch:
            contract.deliverables = patch["deliverables"]

        if "validation" in patch:
            contract.validation = patch["validation"]

        if "constraints" in patch:
            contract.constraints = patch["constraints"]

        if "context" in patch:
            contract.context = patch["context"]

        return {"ok": True, "task": task.model_copy(update={"contract": contract})}

    return _update_task_by_id(board, taskId, updater)


def addTaskContractDeliverable(
    board: Board, taskId: str, deliverable: Deliverable
) -> BoardOperationResult:
    """Add a deliverable to a task's contract."""

    res = _normalize_non_empty(deliverable.path, "Deliverable path is required")
    if not res["ok"]:
        return BoardOperationResult(success=False, error=res["error"])
    normalized_path = res["value"]

    def updater(task: Task) -> TaskUpdate:
        c_res = _get_contract(task)
        if not c_res["ok"]:
            return {"ok": False, "error": c_res["error"]}

        contract = c_res["contract"]
        current = contract.deliverables or []
        if any(d.path == normalized_path for d in current):
            return {
                "ok": False,
                "error": f"Deliverable {normalized_path} already exists",
            }

        new_deliverable = deliverable.model_copy(update={"path": normalized_path})
        next_deliverables = current + [new_deliverable]
        new_contract = contract.model_copy(update={"deliverables": next_deliverables})
        return {"ok": True, "task": task.model_copy(update={"contract": new_contract})}

    return _update_task_by_id(board, taskId, updater)


def removeTaskContractDeliverable(
    board: Board, taskId: str, deliverablePath: str
) -> BoardOperationResult:
    """Remove a deliverable from a task's contract (by path)."""

    res = _normalize_non_empty(deliverablePath, "Deliverable path is required")
    if not res["ok"]:
        return BoardOperationResult(success=False, error=res["error"])
    normalized_path = res["value"]

    def updater(task: Task) -> TaskUpdate:
        c_res = _get_contract(task)
        if not c_res["ok"]:
            return {"ok": False, "error": c_res["error"]}

        contract = c_res["contract"]
        current = contract.deliverables or []
        if not any(d.path == normalized_path for d in current):
            return {
                "ok": False,
                "error": f"Deliverable {normalized_path} not found",
            }

        remaining = [d for d in current if d.path != normalized_path]
        new_contract = contract.model_copy(
            update={"deliverables": remaining if remaining else None}
        )
        return {"ok": True, "task": task.model_copy(update={"contract": new_contract})}

    return _update_task_by_id(board, taskId, updater)


def addTaskContractValidationCommand(
    board: Board, taskId: str, command: str
) -> BoardOperationResult:
    """Add a validation command to a task's contract."""

    res = _normalize_non_empty(command, "Validation command is required")
    if not res["ok"]:
        return BoardOperationResult(success=False, error=res["error"])
    normalized = res["value"]

    def updater(task: Task) -> TaskUpdate:
        c_res = _get_contract(task)
        if not c_res["ok"]:
            return {"ok": False, "error": c_res["error"]}

        contract = c_res["contract"]
        current_val = contract.validation or ValidationConfig(commands=[])
        current_commands = current_val.commands or []

        if normalized in current_commands:
            return {"ok": True, "task": task}

        next_commands = current_commands + [normalized]
        new_val = current_val.model_copy(update={"commands": next_commands})
        new_contract = contract.model_copy(update={"validation": new_val})
        return {"ok": True, "task": task.model_copy(update={"contract": new_contract})}

    return _update_task_by_id(board, taskId, updater)


def removeTaskContractValidationCommand(
    board: Board, taskId: str, command: str
) -> BoardOperationResult:
    """Remove a validation command from a task's contract."""

    res = _normalize_non_empty(command, "Validation command is required")
    if not res["ok"]:
        return BoardOperationResult(success=False, error=res["error"])
    normalized = res["value"]

    def updater(task: Task) -> TaskUpdate:
        c_res = _get_contract(task)
        if not c_res["ok"]:
            return {"ok": False, "error": c_res["error"]}

        contract = c_res["contract"]
        if not contract.validation or not contract.validation.commands:
            return {"ok": False, "error": "Validation command not found"}

        current_commands = contract.validation.commands
        if normalized not in current_commands:
            return {"ok": False, "error": "Validation command not found"}

        remaining = [c for c in current_commands if c != normalized]
        if remaining:
            new_val = contract.validation.model_copy(update={"commands": remaining})
            new_contract = contract.model_copy(update={"validation": new_val})
        else:
            new_contract = contract.model_copy(update={"validation": None})

        return {"ok": True, "task": task.model_copy(update={"contract": new_contract})}

    return _update_task_by_id(board, taskId, updater)


def addTaskContractConstraint(
    board: Board, taskId: str, constraint: str
) -> BoardOperationResult:
    """Add a constraint to a task's contract."""

    res = _normalize_non_empty(constraint, "Constraint is required")
    if not res["ok"]:
        return BoardOperationResult(success=False, error=res["error"])
    normalized = res["value"]

    def updater(task: Task) -> TaskUpdate:
        c_res = _get_contract(task)
        if not c_res["ok"]:
            return {"ok": False, "error": c_res["error"]}

        contract = c_res["contract"]
        current = contract.constraints or []
        if normalized in current:
            return {"ok": True, "task": task}

        next_constraints = current + [normalized]
        new_contract = contract.model_copy(update={"constraints": next_constraints})
        return {"ok": True, "task": task.model_copy(update={"contract": new_contract})}

    return _update_task_by_id(board, taskId, updater)


def removeTaskContractConstraint(
    board: Board, taskId: str, constraint: str
) -> BoardOperationResult:
    """Remove a constraint from a task's contract."""

    res = _normalize_non_empty(constraint, "Constraint is required")
    if not res["ok"]:
        return BoardOperationResult(success=False, error=res["error"])
    normalized = res["value"]

    def updater(task: Task) -> TaskUpdate:
        c_res = _get_contract(task)
        if not c_res["ok"]:
            return {"ok": False, "error": c_res["error"]}

        contract = c_res["contract"]
        current = contract.constraints or []
        if normalized not in current:
            return {"ok": False, "error": "Constraint not found"}

        remaining = [c for c in current if c != normalized]
        new_contract = contract.model_copy(
            update={"constraints": remaining if remaining else None}
        )
        return {"ok": True, "task": task.model_copy(update={"contract": new_contract})}

    return _update_task_by_id(board, taskId, updater)
