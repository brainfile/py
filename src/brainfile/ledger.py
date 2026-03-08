"""Ledger utilities for append-only task completion history (``logs/ledger.jsonl``)."""

from __future__ import annotations

import json
import math
import os
import warnings
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, TypeVar

from ._time import utc_now_iso
from .models import Deliverable, Task, TaskDocument
from .task_file import read_tasks_dir
from .types_ledger import (
    LEDGER_CONTRACT_STATUSES,
    BuildLedgerRecordOptions,
    FileHistoryOptions,
    LedgerContractStatus,
    LedgerDateRange,
    LedgerQueryFilters,
    LedgerRecord,
    LedgerRecordType,
    TaskContextEntry,
    TaskContextOptions,
)

LEDGER_FILE_NAME = "ledger.jsonl"
EPOCH_ISO = "1970-01-01T00:00:00.000Z"
_LEGACY_WARNING_TRACKER: set[str] = set()


def _get_ledger_path(logs_dir: str) -> str:
    return os.path.join(logs_dir, LEDGER_FILE_NAME)


def normalize_path_value(value: str) -> str:
    """Normalize path strings to TS-compatible slash separators and prefixes."""

    normalized = value.strip().replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _to_unique_strings(values: Sequence[str] | None) -> list[str]:
    if not values:
        return []

    unique: set[str] = set()
    result: list[str] = []

    for value in values:
        trimmed = value.strip()
        if not trimmed or trimmed in unique:
            continue
        unique.add(trimmed)
        result.append(trimmed)

    return result


def _to_unique_paths(values: Sequence[str] | None) -> list[str]:
    if not values:
        return []

    unique: set[str] = set()
    result: list[str] = []

    for value in values:
        trimmed = value.strip()
        if not trimmed:
            continue

        normalized = normalize_path_value(trimmed)
        if normalized in unique:
            continue

        unique.add(normalized)
        result.append(normalized)

    return result


def _parse_timestamp(value: str | None) -> float | None:
    if not value:
        return None

    try:
        if value.endswith("Z"):
            dt = datetime.fromisoformat(value[:-1] + "+00:00")
        else:
            dt = datetime.fromisoformat(value)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.timestamp() * 1000


def _timestamp_or(value: str | None, fallback: float) -> float:
    parsed = _parse_timestamp(value)
    return fallback if parsed is None else parsed


def _range_bound_ms(value: str | None) -> float | None:
    return _parse_timestamp(value) if value else None


def _matches_date_range(completed_at: str, date_range: LedgerDateRange | None) -> bool:
    if date_range is None:
        return True

    completed_ms = _parse_timestamp(completed_at)
    if completed_ms is None:
        return False

    from_ms = _range_bound_ms(date_range.from_)
    to_ms = _range_bound_ms(date_range.to)
    return (from_ms is None or completed_ms >= from_ms) and (to_ms is None or completed_ms <= to_ms)


def _is_ledger_type(value: str | None) -> bool:
    return value in {"task", "epic", "adr"}


def _normalize_ledger_type(task: Task) -> LedgerRecordType:
    if _is_ledger_type(task.type):
        return task.type  # type: ignore[return-value]
    if task.id.startswith("epic-"):
        return "epic"
    if task.id.startswith("adr-"):
        return "adr"
    return "task"


def is_ledger_contract_status(value: str | None) -> bool:
    """Return True when value is one of the ledger contract statuses."""

    return value in LEDGER_CONTRACT_STATUSES


def _extract_deliverable_paths(deliverables: Sequence[Deliverable] | None) -> list[str]:
    if not deliverables:
        return []
    return _to_unique_paths([deliverable.path for deliverable in deliverables])


def _normalize_task_input(task_or_document: TaskDocument | Task) -> Task:
    if isinstance(task_or_document, TaskDocument):
        return task_or_document.task
    return task_or_document


def _derive_summary(body: str, fallback_title: str) -> str:
    for line in body.split("\n"):
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        return trimmed
    return f"Completed: {fallback_title}"


def _default_files_changed(task: Task) -> list[str]:
    deliverables = _extract_deliverable_paths(task.contract.deliverables if task.contract else None)
    if deliverables:
        return deliverables

    related_files = _to_unique_paths(task.related_files)
    if related_files:
        return related_files

    return [f"{task.id}.md"]


def _compute_cycle_time_hours(created_at: str, completed_at: str) -> int | float:
    created_ms = _parse_timestamp(created_at)
    completed_ms = _parse_timestamp(completed_at)
    if created_ms is None or completed_ms is None:
        return 0

    elapsed_hours = (completed_ms - created_ms) / (1000 * 60 * 60)
    if not math.isfinite(elapsed_hours) or elapsed_hours < 0:
        return 0

    rounded = float(f"{elapsed_hours:.3f}")
    if rounded.is_integer():
        return int(rounded)
    return rounded


def _normalize_validation_attempts(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        return None

    return math.floor(numeric)


def _count_subtasks(task: Task) -> tuple[int, int, bool]:
    if task.subtasks is None:
        return 0, 0, False

    completed = 0
    for subtask in task.subtasks:
        if subtask.completed:
            completed += 1

    return len(task.subtasks), completed, True


def _normalize_contract_status(task: Task) -> LedgerContractStatus | None:
    status = task.contract.status if task.contract else None
    if isinstance(status, str) and is_ledger_contract_status(status):
        return status  # type: ignore[return-value]
    return None


def _path_matches(left: str, right: str) -> bool:
    normalized_left = normalize_path_value(left)
    normalized_right = normalize_path_value(right)

    if not normalized_left or not normalized_right:
        return False

    return (
        normalized_left == normalized_right
        or normalized_left.endswith(f"/{normalized_right}")
        or normalized_right.endswith(f"/{normalized_left}")
    )


def _collect_record_files(record: LedgerRecord) -> list[str]:
    return _to_unique_paths(
        [
            *(record.files_changed or []),
            *(record.related_files or []),
            *(record.deliverables or []),
        ]
    )


def _collect_deliverable_input_paths(
    deliverables: Sequence[str | Deliverable] | None,
) -> list[str]:
    if not deliverables:
        return []

    paths: list[str] = []
    for deliverable in deliverables:
        if isinstance(deliverable, str):
            paths.append(deliverable)
            continue
        paths.append(deliverable.path)

    return _to_unique_paths(paths)


def _matched_files_for_scope(scope_files: Sequence[str], record_files: Sequence[str]) -> list[str]:
    matched: list[str] = []
    for scope_file in scope_files:
        if any(_path_matches(record_file, scope_file) for record_file in record_files):
            matched.append(scope_file)
    return matched


def _warn_invalid_ledger_line(
    line_number: int,
    ledger_path: str,
    detail: str | None = None,
) -> None:
    message = f"[brainfile/core] Ignoring invalid ledger line {line_number} in {ledger_path}"
    if detail:
        message = f"{message}: {detail}"
    warnings.warn(message, stacklevel=2)


def _parse_ledger_line(line: str, line_number: int, ledger_path: str) -> LedgerRecord | None:
    try:
        parsed = json.loads(line)
    except json.JSONDecodeError as error:
        warnings.warn(
            f"[brainfile/core] Failed to parse ledger line {line_number} in "
            f"{ledger_path}: {error.msg}",
            stacklevel=2,
        )
        return None

    if not isinstance(parsed, Mapping):
        _warn_invalid_ledger_line(line_number, ledger_path)
        return None

    try:
        return LedgerRecord.model_validate(parsed)
    except Exception as error:  # noqa: BLE001
        _warn_invalid_ledger_line(line_number, ledger_path, str(error))
        return None


def _should_warn_legacy_fallback(logs_dir: str) -> bool:
    key = os.path.abspath(logs_dir)
    if key in _LEGACY_WARNING_TRACKER:
        return False
    _LEGACY_WARNING_TRACKER.add(key)
    return True


def _read_legacy_markdown_ledger(logs_dir: str) -> list[LedgerRecord]:
    docs = read_tasks_dir(logs_dir)
    if not docs:
        return []

    if _should_warn_legacy_fallback(logs_dir):
        warnings.warn(
            f"[brainfile/core] ledger.jsonl not found in {logs_dir}; "
            "falling back to legacy markdown logs.",
            stacklevel=2,
        )

    records: list[LedgerRecord] = []
    for doc in docs:
        completed_at = (
            doc.task.completed_at
            or doc.task.updated_at
            or doc.task.created_at
            or EPOCH_ISO
        )
        options = BuildLedgerRecordOptions(completed_at=completed_at)
        records.append(build_ledger_record(doc.task, doc.body, options))
    return records


def _normalize_model(cls: type, value: Any) -> Any:
    """Normalize a value to the given model class.

    Accepts an instance, a dict, or None (returns default instance).
    """
    if value is None:
        return cls()
    if isinstance(value, cls):
        return value
    if isinstance(value, Mapping):
        return cls.model_validate(dict(value))
    return cls()


def _record_files_changed(task: Task, build_options: BuildLedgerRecordOptions) -> list[str]:
    files_changed = _to_unique_paths(build_options.files_changed)
    return files_changed if files_changed else _default_files_changed(task)


def _record_summary(task: Task, body: str, build_options: BuildLedgerRecordOptions) -> str:
    summary = build_options.summary.strip() if build_options.summary else ""
    return summary or _derive_summary(body, task.title)


def _record_column_history(task: Task, build_options: BuildLedgerRecordOptions) -> list[str]:
    column_history_input = (
        build_options.column_history
        if build_options.column_history is not None
        else ([task.column] if task.column else None)
    )
    return _to_unique_strings(column_history_input)


def _record_validation_attempts(task: Task, build_options: BuildLedgerRecordOptions) -> int | None:
    validation_attempts_source: object | None = build_options.validation_attempts
    if validation_attempts_source is None and task.contract and task.contract.metrics:
        validation_attempts_source = task.contract.metrics.rework_count
    return _normalize_validation_attempts(validation_attempts_source)


def _apply_task_metadata_fields(
    record: LedgerRecord,
    task: Task,
    column_history: list[str],
    tags: list[str],
    related_files: list[str],
    deliverables: list[str],
) -> None:
    if column_history:
        record.column_history = column_history
    if task.assignee:
        record.assignee = task.assignee
    if task.priority:
        record.priority = task.priority
    if tags:
        record.tags = tags
    if task.parent_id:
        record.parent_id = task.parent_id
    if related_files:
        record.related_files = related_files
    if deliverables:
        record.deliverables = deliverables


def _apply_contract_metadata_fields(
    record: LedgerRecord,
    contract_status: LedgerContractStatus | None,
    validation_attempts: int | None,
    constraints: list[str],
) -> None:
    if contract_status:
        record.contract_status = contract_status
    if validation_attempts is not None:
        record.validation_attempts = validation_attempts
    if constraints:
        record.constraints = constraints


def _apply_subtask_metadata_fields(
    record: LedgerRecord,
    subtasks_total: int,
    subtasks_completed: int,
    has_subtasks: bool,
) -> None:
    if has_subtasks:
        record.subtasks_completed = subtasks_completed
        record.subtasks_total = subtasks_total


def _apply_optional_record_fields(
    record: LedgerRecord,
    task: Task,
    column_history: list[str],
    tags: list[str],
    related_files: list[str],
    deliverables: list[str],
    contract_status: LedgerContractStatus | None,
    validation_attempts: int | None,
    constraints: list[str],
    subtasks_total: int,
    subtasks_completed: int,
    has_subtasks: bool,
) -> None:
    _apply_task_metadata_fields(record, task, column_history, tags, related_files, deliverables)
    _apply_contract_metadata_fields(record, contract_status, validation_attempts, constraints)
    _apply_subtask_metadata_fields(record, subtasks_total, subtasks_completed, has_subtasks)


def build_ledger_record(
    task_or_document: TaskDocument | Task,
    body: str,
    options: BuildLedgerRecordOptions | Mapping[str, object] | None = None,
) -> LedgerRecord:
    """Build a single ledger record from task metadata and markdown body."""

    task = _normalize_task_input(task_or_document)
    build_options = _normalize_model(BuildLedgerRecordOptions, options)

    completed_at = build_options.completed_at or task.completed_at or utc_now_iso()
    created_at = task.created_at or completed_at

    deliverables = _extract_deliverable_paths(task.contract.deliverables if task.contract else None)
    tags = _to_unique_strings(task.tags)
    related_files = _to_unique_paths(task.related_files)
    constraints = _to_unique_strings(task.contract.constraints if task.contract else None)
    column_history = _record_column_history(task, build_options)
    contract_status = _normalize_contract_status(task)
    validation_attempts = _record_validation_attempts(task, build_options)
    subtasks_total, subtasks_completed, has_subtasks = _count_subtasks(task)

    record = LedgerRecord(
        id=task.id,
        type=_normalize_ledger_type(task),
        title=task.title,
        files_changed=_record_files_changed(task, build_options),
        created_at=created_at,
        completed_at=completed_at,
        cycle_time_hours=_compute_cycle_time_hours(created_at, completed_at),
        summary=_record_summary(task, body, build_options),
    )

    _apply_optional_record_fields(
        record,
        task,
        column_history,
        tags,
        related_files,
        deliverables,
        contract_status,
        validation_attempts,
        constraints,
        subtasks_total,
        subtasks_completed,
        has_subtasks,
    )
    return record


def append_ledger_record(logs_dir: str, record: LedgerRecord) -> str:
    """Append a single record to ``logs/ledger.jsonl`` and return the file path."""

    os.makedirs(logs_dir, exist_ok=True)
    ledger_path = _get_ledger_path(logs_dir)
    payload = record.model_dump(by_alias=True, exclude_none=True)
    line = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    with open(ledger_path, "a", encoding="utf-8") as file:
        file.write(f"{line}\n")
    return ledger_path


def read_ledger(logs_dir: str) -> list[LedgerRecord]:
    """
    Read all ledger records.

    Backward compatibility: if ``ledger.jsonl`` is missing but markdown logs
    exist, they are converted on read with a warning.
    """

    ledger_path = _get_ledger_path(logs_dir)
    if not os.path.exists(ledger_path):
        return _read_legacy_markdown_ledger(logs_dir)

    with open(ledger_path, encoding="utf-8") as file:
        lines = file.read().split("\n")

    records: list[LedgerRecord] = []
    for index, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        parsed = _parse_ledger_line(line, index, ledger_path)
        if parsed:
            records.append(parsed)

    return records


def _status_filter_set(status_values: str | list[str] | None) -> set[str] | None:
    if isinstance(status_values, str):
        return {status_values}
    return set(status_values) if status_values else None


def _matches_query_tags(record: LedgerRecord, query_tags: list[str] | None) -> bool:
    if not query_tags:
        return True
    record_tags = [tag.lower() for tag in (record.tags or [])]
    return any(tag in record_tags for tag in query_tags)


def _matches_query_status(record: LedgerRecord, status_set: set[str] | None) -> bool:
    return not status_set or bool(record.contract_status and record.contract_status in status_set)


def _matches_query_files(record: LedgerRecord, query_files: list[str] | None) -> bool:
    if not query_files:
        return True
    record_files = _collect_record_files(record)
    return any(
        _path_matches(record_file, query_file)
        for query_file in query_files
        for record_file in record_files
    )


def _record_matches_query(
    record: LedgerRecord,
    query_filters: LedgerQueryFilters,
    query_tags: list[str] | None,
    status_set: set[str] | None,
    query_files: list[str] | None,
) -> bool:
    if query_filters.assignee and record.assignee != query_filters.assignee:
        return False
    if query_filters.date_range and not _matches_date_range(
        record.completed_at,
        query_filters.date_range,
    ):
        return False
    return (
        _matches_query_tags(record, query_tags)
        and _matches_query_status(record, status_set)
        and _matches_query_files(record, query_files)
    )


def query_ledger(
    logs_dir: str,
    filters: LedgerQueryFilters | Mapping[str, object] | None = None,
) -> list[LedgerRecord]:
    """Query ledger records using indexed filters in a single pass."""

    query_filters = _normalize_model(LedgerQueryFilters, filters)
    query_tags = [tag.lower() for tag in query_filters.tags] if query_filters.tags else None
    status_set = _status_filter_set(query_filters.contract_status)
    query_files = _to_unique_paths(query_filters.files) if query_filters.files else None

    filtered: list[LedgerRecord] = []
    for record in read_ledger(logs_dir):
        if _record_matches_query(record, query_filters, query_tags, status_set, query_files):
            filtered.append(record)
    return filtered


def _record_matches_file_history(
    record: LedgerRecord,
    normalized_target: str,
    history_options: FileHistoryOptions,
) -> bool:
    if not any(
        _path_matches(changed_file, normalized_target)
        for changed_file in (record.files_changed or [])
    ):
        return False
    return not history_options.date_range or _matches_date_range(
        record.completed_at,
        history_options.date_range,
    )


_RecordT = TypeVar("_RecordT")


def _apply_record_limit(records: list[_RecordT], limit: int | None) -> list[_RecordT]:
    if limit is not None and limit > 0:
        return records[:limit]
    return records


def get_file_history(
    logs_dir: str,
    file_path: str,
    options: FileHistoryOptions | Mapping[str, object] | None = None,
) -> list[LedgerRecord]:
    """Get file history from records whose ``filesChanged`` include the target path."""

    history_options = _normalize_model(FileHistoryOptions, options)
    normalized_target = normalize_path_value(file_path)
    if not normalized_target:
        return []

    records = [
        record
        for record in read_ledger(logs_dir)
        if _record_matches_file_history(record, normalized_target, history_options)
    ]
    records.sort(key=lambda record: _timestamp_or(record.completed_at, 0), reverse=True)
    return _apply_record_limit(records, history_options.limit)


def _build_task_context_entry(
    record: LedgerRecord,
    scope_files: list[str],
    context_options: TaskContextOptions,
) -> TaskContextEntry | None:
    if context_options.date_range and not _matches_date_range(
        record.completed_at,
        context_options.date_range,
    ):
        return None

    matched_files = _matched_files_for_scope(scope_files, _collect_record_files(record))
    if not matched_files:
        return None

    return TaskContextEntry(record=record, matched_files=matched_files)


def get_task_context(
    logs_dir: str,
    related_files: Sequence[str],
    deliverables: Sequence[str | Deliverable] | None = None,
    options: TaskContextOptions | Mapping[str, object] | None = None,
) -> list[TaskContextEntry]:
    """Build recent task context by intersecting task scope files with ledger history."""

    context_options = _normalize_model(TaskContextOptions, options)
    scope_files = _to_unique_paths(
        [*related_files, *_collect_deliverable_input_paths(deliverables)]
    )
    if not scope_files:
        return []

    entries = [
        entry
        for record in read_ledger(logs_dir)
        for entry in [_build_task_context_entry(record, scope_files, context_options)]
        if entry is not None
    ]
    entries.sort(key=lambda entry: _timestamp_or(entry.record.completed_at, 0), reverse=True)
    return _apply_record_limit(entries, context_options.limit)


__all__ = [
    "build_ledger_record",
    "append_ledger_record",
    "read_ledger",
    "query_ledger",
    "get_file_history",
    "get_task_context",
    "normalize_path_value",
    "is_ledger_contract_status",
]
