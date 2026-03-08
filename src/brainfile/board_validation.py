from __future__ import annotations

from .models import BoardConfig, TypesConfig

__all__ = ["get_board_types", "validate_type", "validate_column", "BoardValidationResult"]

BoardValidationResult = dict[str, bool | str | None]


def get_board_types(board: BoardConfig) -> TypesConfig:
    return board.types or {}


def _ok() -> BoardValidationResult:
    return {"valid": True}


def _err(message: str) -> BoardValidationResult:
    return {"valid": False, "error": message}


def _available_type_names(types: TypesConfig) -> list[str]:
    names = list(types)
    return names if "task" in types else ["task", *names]


def validate_type(board: BoardConfig, type_name: str) -> BoardValidationResult:
    if not board.strict:
        return _ok()

    types = get_board_types(board)
    if not types or type_name == "task" or type_name in types:
        return _ok()

    available = ", ".join(_available_type_names(types))
    return _err(f"Type '{type_name}' is not defined. Available types: {available}")


def validate_column(board: BoardConfig, column_id: str) -> BoardValidationResult:
    column_ids = [column.id for column in board.columns]
    if not board.strict or column_id in column_ids:
        return _ok()
    return _err(f"Column '{column_id}' is not defined. Available columns: {', '.join(column_ids)}")
