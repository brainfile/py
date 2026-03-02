"""Tests for ledger append/query/context behavior."""

from __future__ import annotations

import os
import pathlib
import warnings

import pytest

from brainfile.ledger import (
    append_ledger_record,
    build_ledger_record,
    get_file_history,
    get_task_context,
    is_ledger_contract_status,
    normalize_path_value,
    query_ledger,
    read_ledger,
)
from brainfile.models import Deliverable, Task
from brainfile.task_file import read_task_file, write_task_file
from brainfile.task_operations import add_task_file, complete_task_file
from brainfile.types_ledger import (
    BuildLedgerRecordOptions,
    FileHistoryOptions,
    LedgerDateRange,
    LedgerQueryFilters,
    LedgerRecord,
    TaskContextOptions,
)


def make_record(**overrides: object) -> LedgerRecord:
    base: dict[str, object] = {
        "id": "task-1",
        "type": "task",
        "title": "Default title",
        "filesChanged": ["src/default.ts"],
        "createdAt": "2026-01-01T00:00:00.000Z",
        "completedAt": "2026-01-01T01:00:00.000Z",
        "cycleTimeHours": 1,
        "summary": "Default summary",
    }
    base.update(overrides)
    return LedgerRecord.model_validate(base)


def test_build_ledger_record_from_task_and_options() -> None:
    task = Task.model_validate(
        {
            "id": "task-12",
            "type": "task",
            "title": "Implement ledger internals",
            "column": "done",
            "assignee": "alice",
            "priority": "high",
            "tags": ["core", "ledger"],
            "parentId": "epic-2",
            "relatedFiles": ["core/src/ledger.ts"],
            "createdAt": "2026-01-01T00:00:00.000Z",
            "subtasks": [
                {"id": "task-12-1", "title": "types", "completed": True},
                {"id": "task-12-2", "title": "tests", "completed": False},
            ],
            "contract": {
                "status": "done",
                "deliverables": [{"type": "file", "path": "core/src/ledger.ts"}],
                "constraints": ["Use append-only writes"],
                "metrics": {"reworkCount": 2},
            },
        }
    )

    record = build_ledger_record(
        task,
        "## Summary\nImplemented ledger internals.\n",
        BuildLedgerRecordOptions(
            summary="Completed implementation and tests",
            filesChanged=["core/src/ledger.ts", "core/src/__tests__/ledger.test.ts"],
            completedAt="2026-01-02T00:00:00.000Z",
            columnHistory=["todo", "in-progress", "done"],
        ),
    )

    assert record.id == "task-12"
    assert record.type == "task"
    assert record.title == "Implement ledger internals"
    assert record.files_changed == ["core/src/ledger.ts", "core/src/__tests__/ledger.test.ts"]
    assert record.created_at == "2026-01-01T00:00:00.000Z"
    assert record.completed_at == "2026-01-02T00:00:00.000Z"
    assert record.cycle_time_hours == 24
    assert record.summary == "Completed implementation and tests"
    assert record.column_history == ["todo", "in-progress", "done"]
    assert record.contract_status == "done"
    assert record.deliverables == ["core/src/ledger.ts"]
    assert record.validation_attempts == 2
    assert record.subtasks_completed == 1
    assert record.subtasks_total == 2


def test_append_record_jsonl_format_is_ts_compatible(tmp_path: pathlib.Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    record = make_record(
        id="task-1",
        title="One",
        filesChanged=["src/a.ts"],
        createdAt="2026-01-01T00:00:00.000Z",
        completedAt="2026-01-01T01:00:00.000Z",
        cycleTimeHours=1,
        summary="Summary",
    )

    ledger_path = append_ledger_record(str(logs_dir), record)
    assert ledger_path == os.path.join(str(logs_dir), "ledger.jsonl")

    with open(ledger_path, "rb") as file:
        actual = file.read()

    expected = (
        b'{"id":"task-1","type":"task","title":"One","filesChanged":["src/a.ts"],'
        b'"createdAt":"2026-01-01T00:00:00.000Z","completedAt":"2026-01-01T01:00:00.000Z",'
        b'"cycleTimeHours":1,"summary":"Summary"}\n'
    )
    assert actual == expected


def test_append_and_read_ledger_records(tmp_path: pathlib.Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    append_ledger_record(
        str(logs_dir),
        make_record(id="task-1", title="One", completedAt="2026-01-01T01:00:00.000Z"),
    )
    append_ledger_record(
        str(logs_dir),
        make_record(id="task-2", title="Two", completedAt="2026-01-02T01:00:00.000Z"),
    )

    records = read_ledger(str(logs_dir))
    assert [record.id for record in records] == ["task-1", "task-2"]


def test_read_ledger_falls_back_to_legacy_markdown_logs(tmp_path: pathlib.Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    task = Task(
        id="task-legacy-1",
        title="Legacy completed task",
        completedAt="2026-01-03T10:00:00.000Z",
        createdAt="2026-01-03T08:00:00.000Z",
        relatedFiles=["src/legacy.ts"],
    )
    write_task_file(
        str(logs_dir / "task-legacy-1.md"),
        task,
        "## Summary\nLegacy completion.\n",
    )

    with pytest.warns(UserWarning, match="ledger\\.jsonl not found"):
        records = read_ledger(str(logs_dir))

    assert len(records) == 1
    assert records[0].id == "task-legacy-1"
    assert records[0].summary == "Legacy completion."

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        read_ledger(str(logs_dir))
    assert not any("ledger.jsonl not found" in str(w.message) for w in caught)


def test_query_ledger_filters(tmp_path: pathlib.Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    append_ledger_record(
        str(logs_dir),
        make_record(
            id="task-1",
            assignee="alice",
            tags=["core", "ledger"],
            completedAt="2026-02-05T12:00:00.000Z",
            contractStatus="done",
            filesChanged=["src/ledger.ts"],
        ),
    )
    append_ledger_record(
        str(logs_dir),
        make_record(
            id="task-2",
            assignee="bob",
            tags=["docs"],
            completedAt="2026-02-12T12:00:00.000Z",
            contractStatus="failed",
            filesChanged=["docs/readme.md"],
        ),
    )
    append_ledger_record(
        str(logs_dir),
        make_record(
            id="task-3",
            assignee="alice",
            tags=["ops"],
            completedAt="2026-03-01T12:00:00.000Z",
            contractStatus="done",
            filesChanged=["src/runtime.ts"],
        ),
    )

    filtered = query_ledger(
        str(logs_dir),
        LedgerQueryFilters(
            assignee="alice",
            tags=["ledger"],
            dateRange=LedgerDateRange(
                from_="2026-02-01T00:00:00.000Z",
                to="2026-02-28T23:59:59.999Z",
            ),
            contractStatus="done",
            files=["src/ledger.ts"],
        ),
    )

    assert [record.id for record in filtered] == ["task-1"]


def test_get_file_history_sorted_desc_and_limited(tmp_path: pathlib.Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    append_ledger_record(
        str(logs_dir),
        make_record(
            id="task-1",
            completedAt="2026-02-01T12:00:00.000Z",
            filesChanged=["src/shared.ts"],
        ),
    )
    append_ledger_record(
        str(logs_dir),
        make_record(
            id="task-2",
            completedAt="2026-02-10T12:00:00.000Z",
            filesChanged=["src/unrelated.ts"],
        ),
    )
    append_ledger_record(
        str(logs_dir),
        make_record(
            id="task-3",
            completedAt="2026-02-20T12:00:00.000Z",
            filesChanged=["src/shared.ts"],
        ),
    )

    history = get_file_history(str(logs_dir), "src/shared.ts")
    assert [record.id for record in history] == ["task-3", "task-1"]

    limited = get_file_history(str(logs_dir), "src/shared.ts", FileHistoryOptions(limit=1))
    assert [record.id for record in limited] == ["task-3"]


def test_get_task_context_from_file_intersections(tmp_path: pathlib.Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    append_ledger_record(
        str(logs_dir),
        make_record(
            id="task-1",
            completedAt="2026-02-01T12:00:00.000Z",
            filesChanged=["src/shared.ts"],
            deliverables=["docs/spec.md"],
        ),
    )
    append_ledger_record(
        str(logs_dir),
        make_record(
            id="task-2",
            completedAt="2026-02-11T12:00:00.000Z",
            filesChanged=["src/another.ts"],
            relatedFiles=["docs/spec.md"],
        ),
    )
    append_ledger_record(
        str(logs_dir),
        make_record(
            id="task-3",
            completedAt="2026-02-20T12:00:00.000Z",
            filesChanged=["src/unrelated.ts"],
        ),
    )

    context = get_task_context(
        str(logs_dir),
        ["src/shared.ts"],
        [Deliverable(type="file", path="docs/spec.md")],
    )

    assert [entry.record.id for entry in context] == ["task-2", "task-1"]
    assert "docs/spec.md" in context[0].matched_files
    assert "src/shared.ts" in context[1].matched_files

    limited = get_task_context(
        str(logs_dir),
        ["src/shared.ts"],
        [Deliverable(type="file", path="docs/spec.md")],
        TaskContextOptions(limit=1),
    )
    assert len(limited) == 1
    assert limited[0].record.id == "task-2"


def test_normalize_path_and_contract_status_helpers() -> None:
    assert normalize_path_value(".\\src\\app.ts") == "src/app.ts"
    assert normalize_path_value(" ./docs/readme.md ") == "docs/readme.md"

    assert is_ledger_contract_status("done") is True
    assert is_ledger_contract_status("blocked") is True
    assert is_ledger_contract_status("draft") is False
    assert is_ledger_contract_status(None) is False


def test_complete_task_file_writes_ledger_and_deletes_board_file(
    tmp_path: pathlib.Path,
) -> None:
    board_dir = tmp_path / "board"
    logs_dir = tmp_path / "logs"
    board_dir.mkdir()
    logs_dir.mkdir()

    create_result = add_task_file(
        str(board_dir),
        {
            "id": "task-1",
            "title": "Task 1",
            "column": "done",
            "related_files": ["src/app.ts"],
        },
        body="## Summary\nImplemented the final piece.\n",
    )
    assert create_result["success"] is True

    task_path = create_result["file_path"]
    result = complete_task_file(task_path, str(logs_dir))
    assert result["success"] is True
    assert os.path.exists(task_path) is False
    assert result["task"] is not None
    assert result["task"].completed_at is not None
    assert result["task"].column is None
    assert result["task"].position is None

    ledger_path = os.path.join(str(logs_dir), "ledger.jsonl")
    assert result["file_path"] == ledger_path
    assert os.path.exists(ledger_path) is True
    assert os.path.exists(os.path.join(str(logs_dir), "task-1.md")) is False

    records = read_ledger(str(logs_dir))
    assert len(records) == 1
    assert records[0].id == "task-1"
    assert records[0].summary == "Implemented the final piece."
    assert records[0].files_changed == ["src/app.ts"]


def test_complete_task_file_legacy_mode_keeps_markdown_flow(
    tmp_path: pathlib.Path,
) -> None:
    board_dir = tmp_path / "board"
    logs_dir = tmp_path / "logs"
    board_dir.mkdir()
    logs_dir.mkdir()

    create_result = add_task_file(
        str(board_dir),
        {
            "id": "task-1",
            "title": "Task 1",
            "column": "done",
        },
        body="## Log\n- Started work\n",
    )
    assert create_result["success"] is True

    task_path = create_result["file_path"]
    result = complete_task_file(task_path, str(logs_dir), legacy_mode=True)
    assert result["success"] is True
    assert os.path.exists(task_path) is False
    assert os.path.exists(os.path.join(str(logs_dir), "task-1.md")) is True
    assert os.path.exists(os.path.join(str(logs_dir), "ledger.jsonl")) is False

    doc = read_task_file(os.path.join(str(logs_dir), "task-1.md"))
    assert doc is not None
    assert "## Log" in doc.body
    assert "Started work" in doc.body
