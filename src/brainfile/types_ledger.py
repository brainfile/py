"""Dataclass models for ledger records and query options.

Replaces Pydantic models with plain dataclasses using the _ModelMixin
for model_validate / model_dump / model_copy compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, get_args

from .models import PriorityLiteral, _ModelMixin

LedgerRecordType = Literal["task", "epic", "adr"]

LedgerContractStatus = Literal[
    "ready",
    "in_progress",
    "delivered",
    "done",
    "failed",
    "blocked",
]
LEDGER_CONTRACT_STATUSES: tuple[str, ...] = get_args(LedgerContractStatus)


@dataclass
class LedgerRecord(_ModelMixin):
    """Single record persisted in ``logs/ledger.jsonl``."""

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
    """Optional fields for ``build_ledger_record``."""

    summary: str | None = None
    files_changed: list[str] | None = None
    completed_at: str | None = None
    column_history: list[str] | None = None
    validation_attempts: int | None = None


@dataclass
class LedgerDateRange(_ModelMixin):
    """Date range filter for ledger queries."""

    from_: str | None = None
    to: str | None = None

    @classmethod
    def model_validate(cls, data: dict | LedgerDateRange | None) -> LedgerDateRange:
        if data is None:
            return cls()
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        # Handle 'from' alias
        kwargs = {}
        if "from" in data:
            kwargs["from_"] = data["from"]
        if "from_" in data:
            kwargs["from_"] = data["from_"]
        if "to" in data:
            kwargs["to"] = data["to"]
        return cls(**kwargs)


@dataclass
class LedgerQueryFilters(_ModelMixin):
    """Filters for ``query_ledger``."""

    assignee: str | None = None
    tags: list[str] | None = None
    date_range: LedgerDateRange | None = None
    contract_status: str | list[str] | None = None
    files: list[str] | None = None

    @classmethod
    def model_validate(cls, data: dict | LedgerQueryFilters | None) -> LedgerQueryFilters:
        if data is None:
            return cls()
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        kwargs: dict = {}
        for key, value in data.items():
            snake_key = key
            if key == "dateRange":
                snake_key = "date_range"
            elif key == "contractStatus":
                snake_key = "contract_status"
            if snake_key == "date_range" and isinstance(value, dict):
                kwargs[snake_key] = LedgerDateRange.model_validate(value)
            else:
                kwargs[snake_key] = value
        return cls(**kwargs)


@dataclass
class FileHistoryOptions(_ModelMixin):
    """Options for ``get_file_history``."""

    limit: int | None = None
    date_range: LedgerDateRange | None = None

    @classmethod
    def model_validate(cls, data: dict | FileHistoryOptions | None) -> FileHistoryOptions:
        if data is None:
            return cls()
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        kwargs: dict = {}
        for key, value in data.items():
            snake_key = key
            if key == "dateRange":
                snake_key = "date_range"
            if snake_key == "date_range" and isinstance(value, dict):
                kwargs[snake_key] = LedgerDateRange.model_validate(value)
            else:
                kwargs[snake_key] = value
        return cls(**kwargs)


@dataclass
class TaskContextOptions(_ModelMixin):
    """Options for ``get_task_context``."""

    limit: int | None = None
    date_range: LedgerDateRange | None = None

    @classmethod
    def model_validate(cls, data: dict | TaskContextOptions | None) -> TaskContextOptions:
        if data is None:
            return cls()
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        kwargs: dict = {}
        for key, value in data.items():
            snake_key = key
            if key == "dateRange":
                snake_key = "date_range"
            if snake_key == "date_range" and isinstance(value, dict):
                kwargs[snake_key] = LedgerDateRange.model_validate(value)
            else:
                kwargs[snake_key] = value
        return cls(**kwargs)


@dataclass
class TaskContextEntry(_ModelMixin):
    """Matched ledger record and the scoped files that matched it."""

    record: LedgerRecord = field(default_factory=LedgerRecord)
    matched_files: list[str] = field(default_factory=list)

    @classmethod
    def model_validate(cls, data: dict | TaskContextEntry | None) -> TaskContextEntry:
        if data is None:
            return cls()
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        kwargs: dict = {}
        for key, value in data.items():
            snake_key = key
            if key == "matchedFiles":
                snake_key = "matched_files"
            if snake_key == "record" and isinstance(value, dict):
                kwargs[snake_key] = LedgerRecord.model_validate(value)
            else:
                kwargs[snake_key] = value
        return cls(**kwargs)
