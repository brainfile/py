"""Pydantic models for ledger records and query options."""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field

from .models import PriorityLiteral

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


class LedgerRecord(BaseModel):
    """Single record persisted in ``logs/ledger.jsonl``."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    type: LedgerRecordType
    title: str
    files_changed: list[str] = Field(alias="filesChanged")
    created_at: str = Field(alias="createdAt")
    completed_at: str = Field(alias="completedAt")
    cycle_time_hours: int | float = Field(alias="cycleTimeHours")
    summary: str

    column_history: list[str] | None = Field(default=None, alias="columnHistory")
    assignee: str | None = None
    priority: PriorityLiteral | None = None
    tags: list[str] | None = None
    parent_id: str | None = Field(default=None, alias="parentId")
    related_files: list[str] | None = Field(default=None, alias="relatedFiles")
    deliverables: list[str] | None = None
    contract_status: LedgerContractStatus | None = Field(default=None, alias="contractStatus")
    validation_attempts: int | None = Field(default=None, alias="validationAttempts")
    constraints: list[str] | None = None
    subtasks_completed: int | None = Field(default=None, alias="subtasksCompleted")
    subtasks_total: int | None = Field(default=None, alias="subtasksTotal")


class BuildLedgerRecordOptions(BaseModel):
    """Optional fields for ``build_ledger_record``."""

    model_config = ConfigDict(populate_by_name=True)

    summary: str | None = None
    files_changed: list[str] | None = Field(default=None, alias="filesChanged")
    completed_at: str | None = Field(default=None, alias="completedAt")
    column_history: list[str] | None = Field(default=None, alias="columnHistory")
    validation_attempts: int | None = Field(default=None, alias="validationAttempts")


class LedgerDateRange(BaseModel):
    """Date range filter for ledger queries."""

    model_config = ConfigDict(populate_by_name=True)

    from_: str | None = Field(default=None, alias="from")
    to: str | None = None


class LedgerQueryFilters(BaseModel):
    """Filters for ``query_ledger``."""

    model_config = ConfigDict(populate_by_name=True)

    assignee: str | None = None
    tags: list[str] | None = None
    date_range: LedgerDateRange | None = Field(default=None, alias="dateRange")
    contract_status: LedgerContractStatus | list[LedgerContractStatus] | None = Field(
        default=None,
        alias="contractStatus",
    )
    files: list[str] | None = None


class FileHistoryOptions(BaseModel):
    """Options for ``get_file_history``."""

    model_config = ConfigDict(populate_by_name=True)

    limit: int | None = None
    date_range: LedgerDateRange | None = Field(default=None, alias="dateRange")


class TaskContextOptions(BaseModel):
    """Options for ``get_task_context``."""

    model_config = ConfigDict(populate_by_name=True)

    limit: int | None = None
    date_range: LedgerDateRange | None = Field(default=None, alias="dateRange")


class TaskContextEntry(BaseModel):
    """Matched ledger record and the scoped files that matched it."""

    model_config = ConfigDict(populate_by_name=True)

    record: LedgerRecord
    matched_files: list[str] = Field(alias="matchedFiles")
