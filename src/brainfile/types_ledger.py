from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypeVar, get_args

from .models import PriorityLiteral, _ModelMixin

LedgerRecordType = Literal["task", "epic", "adr"]
LedgerContractStatus = Literal["ready", "in_progress", "delivered", "done", "failed", "blocked"]
LEDGER_CONTRACT_STATUSES: tuple[str, ...] = get_args(LedgerContractStatus)

T = TypeVar("T", bound="_ModelMixin")


@dataclass
class LedgerRecord(_ModelMixin):
    id: str = ""
    type: LedgerRecordType = "task"
    title: str = ""
    files_changed: list[str] = field(default_factory=list)
    created_at: str = ""
    completed_at: str = ""
    cycle_time_hours: int | float = 0
    summary: str = ""
    column_history: list[str] | None = None
    assignee: str | None = None
    priority: PriorityLiteral | None = None
    tags: list[str] | None = None
    parent_id: str | None = None
    related_files: list[str] | None = None
    deliverables: list[str] | None = None
    contract_status: LedgerContractStatus | None = None
    validation_attempts: int | None = None
    constraints: list[str] | None = None
    subtasks_completed: int | None = None
    subtasks_total: int | None = None


@dataclass
class BuildLedgerRecordOptions(_ModelMixin):
    summary: str | None = None
    files_changed: list[str] | None = None
    completed_at: str | None = None
    column_history: list[str] | None = None
    validation_attempts: int | None = None


@dataclass
class LedgerDateRange(_ModelMixin):
    from_: str | None = None
    to: str | None = None

    @classmethod
    def model_validate(cls, data: dict[str, Any] | LedgerDateRange | None) -> LedgerDateRange:
        if data is None:
            return cls()
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        return cls(data.get("from_") if "from_" in data else data.get("from"), data.get("to"))


@dataclass
class LedgerQueryFilters(_ModelMixin):
    assignee: str | None = None
    tags: list[str] | None = None
    date_range: LedgerDateRange | None = None
    contract_status: str | list[str] | None = None
    files: list[str] | None = None

    @classmethod
    def model_validate(
        cls,
        data: dict[str, Any] | LedgerQueryFilters | None,
    ) -> LedgerQueryFilters:
        return _alias_model_validate(
            cls,
            data,
            {"dateRange": "date_range", "contractStatus": "contract_status"},
            {"date_range": LedgerDateRange},
        )


@dataclass
class FileHistoryOptions(_ModelMixin):
    limit: int | None = None
    date_range: LedgerDateRange | None = None

    @classmethod
    def model_validate(
        cls,
        data: dict[str, Any] | FileHistoryOptions | None,
    ) -> FileHistoryOptions:
        return _alias_model_validate(
            cls,
            data,
            {"dateRange": "date_range"},
            {"date_range": LedgerDateRange},
        )


@dataclass
class TaskContextOptions(_ModelMixin):
    limit: int | None = None
    date_range: LedgerDateRange | None = None

    @classmethod
    def model_validate(
        cls,
        data: dict[str, Any] | TaskContextOptions | None,
    ) -> TaskContextOptions:
        return _alias_model_validate(
            cls,
            data,
            {"dateRange": "date_range"},
            {"date_range": LedgerDateRange},
        )


@dataclass
class TaskContextEntry(_ModelMixin):
    record: LedgerRecord = field(default_factory=LedgerRecord)
    matched_files: list[str] = field(default_factory=list)

    @classmethod
    def model_validate(
        cls,
        data: dict[str, Any] | TaskContextEntry | None,
    ) -> TaskContextEntry:
        return _alias_model_validate(
            cls,
            data,
            {"matchedFiles": "matched_files"},
            {"record": LedgerRecord},
        )


def _alias_model_validate(
    cls: type[T],
    data: dict[str, Any] | T | None,
    aliases: dict[str, str],
    nested: dict[str, type[_ModelMixin]] | None = None,
) -> T:
    if data is None:
        return cls()
    if isinstance(data, cls):
        return data
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict, got {type(data).__name__}")

    kwargs = {
        aliases.get(key, key): (
            nested[aliases.get(key, key)].model_validate(value)
            if nested and aliases.get(key, key) in nested and isinstance(value, dict)
            else value
        )
        for key, value in data.items()
    }
    return cls(**kwargs)
