"""brainfile.board_validation

Board type/column validation helpers for strict mode.

This mirrors TS core v2 ``boardValidation.ts``.
"""

from __future__ import annotations

from typing import TypedDict

from .models import BoardConfig, TypesConfig


class BoardValidationResult(TypedDict, total=False):
    """Result of a board validation operation."""

    valid: bool
    error: str | None


def get_board_types(board: BoardConfig) -> TypesConfig:
    """Returns the board's type configuration map, or an empty map when absent."""
    return board.types or {}


def validate_type(board: BoardConfig, type_name: str) -> BoardValidationResult:
    """Validates a type name against board config strict mode."""
    if not board.strict or not board.types:
        return {"valid": True}

    if type_name == "task":
        return {"valid": True}

    if type_name in board.types:
        return {"valid": True}

    defined_keys = list(board.types.keys())
    available_types = (
        defined_keys if "task" in defined_keys else ["task"] + defined_keys
    )
    return {
        "valid": False,
        "error": (
            f"Type '{type_name}' is not defined."
            f" Available types: {', '.join(available_types)}"
        ),
    }


def validate_column(board: BoardConfig, column_id: str) -> BoardValidationResult:
    """Validates a column ID against board config strict mode."""
    if not board.strict:
        return {"valid": True}

    column_ids = [column.id for column in board.columns]
    if column_id in column_ids:
        return {"valid": True}

    return {
        "valid": False,
        "error": f"Column '{column_id}' is not defined. Available columns: {', '.join(column_ids)}",
    }
