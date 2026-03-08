from __future__ import annotations

from pathlib import Path

import pytest

from brainfile import (
    AgentInstructions,
    BoardConfig,
    ColumnConfig,
    Contract,
    ContractMetrics,
    Deliverable,
    Task,
    TaskTemplate,
    TemplateVariable,
    compose_body,
    ensure_dirs,
    extract_description,
    extract_log,
    find_workspace_task,
    get_dirs,
    get_log_file_path,
    get_task_file_path,
    is_workspace,
    parse_board_config,
    read_board_config,
    serialize_board_config,
    write_board_config,
    write_task_file,
)
from brainfile.files import (
    BRAINFILE_BASENAME,
    DOT_BRAINFILE_DIRNAME,
    DOT_BRAINFILE_GITIGNORE_BASENAME,
    FoundBrainfile,
    ResolveBrainfilePathOptions,
    ensure_dot_brainfile_dir,
    ensure_dot_brainfile_gitignore,
    find_brainfile,
    get_brainfile_state_dir,
    get_brainfile_state_path,
    get_dot_brainfile_gitignore_path,
    resolve_brainfile_path,
)
from brainfile.formatters import format_task_for_github, format_task_for_linear
from brainfile.id_gen import (
    extract_task_id_number,
    generate_next_subtask_id,
    get_parent_task_id,
    is_valid_subtask_id,
    is_valid_task_id,
)
from brainfile.inference import infer_renderer, infer_type
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
from brainfile.models import Subtask
from brainfile.task_operations import (
    ChildTaskSummary,
    _append_body_section,
    _build_child_tasks_section,
    _extract_epic_child_task_ids,
    _resolve_child_tasks,
    add_task_file,
    append_log,
    complete_task_file,
    delete_task_file,
    find_task,
    generate_next_file_task_id,
    list_tasks,
    move_task_file,
    search_logs,
    search_task_files,
)
from brainfile.templates import (
    BUILT_IN_TEMPLATES,
    generate_subtask_id,
    generate_task_id,
    get_all_template_ids,
    get_template_by_id,
    process_template,
)


def write_brainfile(brainfile_path: Path, content: str | None = None) -> Path:
    brainfile_path.parent.mkdir(parents=True, exist_ok=True)
    brainfile_path.write_text(
        content
        or (
            "---\n"
            "title: Workspace Test\n"
            "columns:\n"
            "- id: todo\n"
            "  title: To Do\n"
            "- id: in-progress\n"
            "  title: In Progress\n"
            "- id: done\n"
            "  title: Done\n"
            "  completionColumn: true\n"
            "---\n"
        ),
        encoding="utf-8",
    )
    return brainfile_path


def test_get_dirs_resolves_workspace_paths(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path / "project"
    workspace_root.mkdir()
    monkeypatch.chdir(workspace_root)

    relative_brainfile = Path(".brainfile") / "brainfile.md"
    dirs = get_dirs(str(relative_brainfile))

    expected_dot_dir = workspace_root / ".brainfile"
    assert dirs.dot_dir == str(expected_dot_dir)
    assert dirs.board_dir == str(expected_dot_dir / "board")
    assert dirs.logs_dir == str(expected_dot_dir / "logs")
    assert dirs.brainfile_path == str(expected_dot_dir / "brainfile.md")


def test_workspace_detection_and_directory_creation(tmp_path: Path) -> None:
    brainfile_path = write_brainfile(tmp_path / ".brainfile" / "brainfile.md")

    assert is_workspace(str(brainfile_path)) is False

    dirs = ensure_dirs(str(brainfile_path))

    assert Path(dirs.board_dir).is_dir()
    assert Path(dirs.logs_dir).is_dir()
    assert is_workspace(str(brainfile_path)) is True


def test_task_and_log_path_helpers_build_canonical_paths(tmp_path: Path) -> None:
    dot_dir = tmp_path / ".brainfile"
    board_dir = dot_dir / "board"
    logs_dir = dot_dir / "logs"

    assert get_task_file_path(str(board_dir), "task-1") == str(board_dir / "task-1.md")
    assert get_log_file_path(str(logs_dir), "task-1") == str(logs_dir / "task-1.md")


def test_find_workspace_task_across_board_and_logs(tmp_path: Path) -> None:
    brainfile_path = write_brainfile(tmp_path / ".brainfile" / "brainfile.md")
    dirs = ensure_dirs(str(brainfile_path))

    active = Task(id="task-1", title="Active", column="todo", position=0)
    completed = Task(
        id="task-2",
        title="Completed",
        column="done",
        completed_at="2026-01-01T00:00:00Z",
    )

    write_task_file(
        get_task_file_path(dirs.board_dir, active.id),
        active,
        compose_body("Active description"),
    )
    write_task_file(
        get_log_file_path(dirs.logs_dir, completed.id),
        completed,
        compose_body("Completed description", "- done"),
    )

    found_active = find_workspace_task(dirs, active.id, search_logs=True)
    assert found_active is not None
    assert found_active["is_log"] is False
    assert found_active["file_path"] == get_task_file_path(dirs.board_dir, active.id)

    assert find_workspace_task(dirs, completed.id, search_logs=False) is None

    found_log = find_workspace_task(dirs, completed.id, search_logs=True)
    assert found_log is not None
    assert found_log["is_log"] is True
    assert found_log["file_path"] == get_log_file_path(dirs.logs_dir, completed.id)


def test_find_workspace_task_scans_nonstandard_filenames(tmp_path: Path) -> None:
    brainfile_path = write_brainfile(tmp_path / ".brainfile" / "brainfile.md")
    dirs = ensure_dirs(str(brainfile_path))

    task = Task(id="task-9", title="Scanned", column="todo")
    nonstandard_path = Path(dirs.board_dir) / "renamed-task.md"
    write_task_file(str(nonstandard_path), task, compose_body("Found by scan"))

    found = find_workspace_task(dirs, task.id)

    assert found is not None
    assert found["is_log"] is False
    assert found["file_path"] == str(nonstandard_path.resolve())


def test_body_helpers_extract_sections_and_compose_markdown() -> None:
    body = compose_body("Line one\nLine two", "- 2026-01-01 started")

    assert extract_description(body) == "Line one\nLine two"
    assert extract_log(body) == "- 2026-01-01 started"

    assert compose_body() == ""
    assert compose_body("Only description") == "## Description\nOnly description\n"
    assert compose_body(log="Only log") == "## Log\nOnly log\n"
    assert extract_description("## Description\n\n## Log\nEntry\n") is None
    assert extract_log("## Description\nBody only\n") is None


def test_board_config_parse_serialize_and_read_round_trip(tmp_path: Path) -> None:
    content = (
        "---\n"
        "title: Workspace Test\n"
        "columns:\n"
        "- id: todo\n"
        "  title: To Do\n"
        "- id: done\n"
        "  title: Done\n"
        "  completionColumn: true\n"
        "agent:\n"
        "  instructions:\n"
        "  - Keep scope tight\n"
        "  identity: Workspace agent\n"
        "---\n"
        "\n"
        "## Notes\n"
        "Workspace-specific notes.\n"
    )

    config, body = parse_board_config(content)

    assert config.title == "Workspace Test"
    assert [column.id for column in config.columns] == ["todo", "done"]
    assert config.columns[1].completion_column is True
    assert config.agent == AgentInstructions(
        instructions=["Keep scope tight"],
        identity="Workspace agent",
    )
    assert body == "## Notes\nWorkspace-specific notes.\n"

    serialized = serialize_board_config(config, body)
    assert "completionColumn: true" in serialized
    assert serialized.endswith("Workspace-specific notes.\n")
    assert "---\n\n## Notes\n" in serialized

    round_trip_config, round_trip_body = parse_board_config(serialized)
    assert round_trip_config == config
    assert round_trip_body == body

    brainfile_path = tmp_path / ".brainfile" / "brainfile.md"
    write_board_config(str(brainfile_path), config, body)

    read_config = read_board_config(str(brainfile_path))
    assert read_config == BoardConfig(
        title="Workspace Test",
        columns=[
            ColumnConfig(id="todo", title="To Do"),
            ColumnConfig(id="done", title="Done", completion_column=True),
        ],
        agent=AgentInstructions(
            instructions=["Keep scope tight"],
            identity="Workspace agent",
        ),
    )


def test_find_workspace_task_returns_none_when_missing(tmp_path: Path) -> None:
    brainfile_path = write_brainfile(tmp_path / ".brainfile" / "brainfile.md")
    dirs = ensure_dirs(str(brainfile_path))

    assert find_workspace_task(dirs, "task-404") is None
    assert find_workspace_task(dirs, "task-404", search_logs=True) is None


@pytest.mark.parametrize(
    ("body", "expected_description", "expected_log"),
    [
        ("", None, None),
        ("## Description\nOnly description\n", "Only description", None),
        ("## Log\nOnly log\n", None, "Only log"),
        ("## Description\nBody\n\n## Notes\nIgnored\n", "Body", None),
    ],
)
def test_extract_helpers_handle_missing_and_partial_sections(
    body: str,
    expected_description: str | None,
    expected_log: str | None,
) -> None:
    assert extract_description(body) == expected_description
    assert extract_log(body) == expected_log


def test_parse_board_config_rejects_invalid_content() -> None:
    with pytest.raises(ValueError, match="Content does not start"):
        parse_board_config("title: Missing frontmatter")

    with pytest.raises(ValueError, match="Missing closing"):
        parse_board_config("---\ntitle: Broken")

    with pytest.raises(ValueError, match="empty or not a mapping"):
        parse_board_config("---\n[]\n---\n")

    with pytest.raises(ValueError, match="Failed to parse YAML frontmatter"):
        parse_board_config("---\ntitle: [unterminated\n---\n")


def test_file_helpers_resolve_and_create_dot_brainfile(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    nested = project / "nested" / "deeper"
    nested.mkdir(parents=True)

    preferred = write_brainfile(project / DOT_BRAINFILE_DIRNAME / BRAINFILE_BASENAME)
    monkeypatch.chdir(nested)

    found = find_brainfile()
    assert found == FoundBrainfile(
        absolute_path=str(preferred),
        project_root=str(project),
        kind="dotdir",
    )

    resolved_default = resolve_brainfile_path()
    assert resolved_default == str(preferred)

    explicit_relative = resolve_brainfile_path(
        ResolveBrainfilePathOptions(file_path="custom.md", start_dir=str(project))
    )
    assert explicit_relative == str(project / "custom.md")

    state_dir = get_brainfile_state_dir(str(project / "brainfile.md"))
    assert state_dir == str(project / DOT_BRAINFILE_DIRNAME)
    assert get_brainfile_state_path(str(project / "brainfile.md")).endswith("state.json")
    assert get_dot_brainfile_gitignore_path(str(project / "brainfile.md")).endswith(
        f"{DOT_BRAINFILE_DIRNAME}/{DOT_BRAINFILE_GITIGNORE_BASENAME}"
    )

    ensured_dir = ensure_dot_brainfile_dir(str(project / "brainfile.md"))
    assert ensured_dir == state_dir
    assert Path(ensured_dir).is_dir()

    ensure_dot_brainfile_gitignore(str(project / "brainfile.md"))
    gitignore_path = Path(get_dot_brainfile_gitignore_path(str(project / "brainfile.md")))
    assert gitignore_path.exists()
    assert gitignore_path.read_text(encoding="utf-8") == ""


def test_id_generation_helpers_cover_valid_and_invalid_cases() -> None:
    assert extract_task_id_number("task-123") == 123
    assert extract_task_id_number("epic-7", prefix="epic") == 7
    assert extract_task_id_number("nope") == 0

    assert generate_next_subtask_id("task-1", ["task-1-1", "task-1-3", "other-1"]) == "task-1-4"

    assert is_valid_task_id("task-5") is True
    assert is_valid_task_id("epic-5", prefix="epic") is True
    assert is_valid_task_id("task-five") is False

    assert is_valid_subtask_id("task-5-2") is True
    assert is_valid_subtask_id("epic-5-2", prefix="epic") is True
    assert is_valid_subtask_id("task-5") is False

    assert get_parent_task_id("task-5-2") == "task-5"
    assert get_parent_task_id("epic-5-2", prefix="epic") == "epic-5"
    assert get_parent_task_id("task-5") is None


def test_formatters_include_expected_sections_and_defaults() -> None:
    task = Task(
        id="task-1",
        title="Ship feature",
        column="done",
        description="Implemented the feature.",
        priority="high",
        tags=["backend"],
        assignee="alice",
        due_date="2026-01-03",
        created_at="2026-01-01T00:00:00Z",
        related_files=["src/app.py"],
        template="feature",
        subtasks=[Subtask(id="task-1-1", title="Write tests", completed=True)],
    )

    github_payload = format_task_for_github(
        task,
        {
            "board_title": "Main Board",
            "from_column": "In Progress",
            "resolved_by": "abc123",
            "resolved_by_pr": "#99",
            "extra_labels": ["release"],
            "include_task_id": True,
        },
    )
    assert github_payload["title"] == "[task-1] Ship feature"
    assert "## Subtasks" in github_payload["body"]
    assert "## Details" in github_payload["body"]
    assert "## Related Files" in github_payload["body"]
    assert "## Resolution" in github_payload["body"]
    assert github_payload["state"] == "closed"
    assert github_payload["labels"] == ["backend", "release", "priority:high", "feature"]

    linear_payload = format_task_for_linear(
        task,
        {
            "board_title": "Main Board",
            "from_column": "In Progress",
            "state_name": "Done",
            "include_task_id": False,
        },
    )
    assert linear_payload["title"] == "Ship feature"
    assert linear_payload["priority"] == 2
    assert linear_payload["labelNames"] == ["backend"]
    assert linear_payload["stateName"] == "Done"
    assert "## Details" in linear_payload["description"]

    low_signal_task = Task(id="task-2", title="Minimal", column="todo")
    minimal_payload = format_task_for_github(low_signal_task, {"include_task_id": False})
    assert minimal_payload["title"] == "Minimal"
    assert minimal_payload["labels"] is None


def test_task_operation_helpers_cover_common_file_flows(tmp_path: Path) -> None:
    brainfile_path = write_brainfile(tmp_path / ".brainfile" / "brainfile.md")
    dirs = ensure_dirs(str(brainfile_path))

    created = add_task_file(
        dirs.board_dir,
        {
            "title": "Implement auth",
            "column": "todo",
            "description": "Auth body",
            "priority": "high",
            "tags": ["api", "auth"],
            "assignee": "alice",
            "related_files": ["src/auth.py"],
            "template": "feature",
            "subtasks": ["Write tests", "Update docs"],
            "parent_id": "epic-1",
        },
        body="## Description\nAuth body\n",
        logs_dir=dirs.logs_dir,
    )
    assert created["success"] is True
    task = created["task"]
    assert task is not None
    assert task.id == "task-1"
    assert task.subtasks is not None
    assert [subtask.id for subtask in task.subtasks] == ["task-1-1", "task-1-2"]

    generated_task_path = Path(get_task_file_path(dirs.board_dir, "task-3"))
    write_task_file(
        str(generated_task_path),
        Task(id="task-3", title="Existing", column="todo"),
        compose_body("existing"),
    )
    write_task_file(
        get_log_file_path(dirs.logs_dir, "task-5"),
        Task(id="task-5", title="Archived", column="done"),
        compose_body("archived"),
    )
    assert generate_next_file_task_id(dirs.board_dir, dirs.logs_dir) == "task-6"

    file_path = created["file_path"]
    assert file_path is not None
    moved = move_task_file(file_path, "in-progress", new_position=3)
    assert moved["success"] is True
    assert moved["task"].column == "in-progress"
    assert moved["task"].position == 3

    appended = append_log(file_path, "Started implementation", agent="agent-1")
    assert appended["success"] is True
    doc = find_task(dirs.board_dir, task.id)
    assert doc is not None
    assert "## Log" in doc.body
    assert "Started implementation" in doc.body

    listed = list_tasks(dirs.board_dir, {"column": "in-progress", "tag": "api", "assignee": "alice"})
    assert [item.task.id for item in listed] == [task.id]

    search_results = search_task_files(dirs.board_dir, "implementation")
    assert [item.task.id for item in search_results] == [task.id]
    assert search_logs(dirs.logs_dir, "archived")[0].task.id == "task-5"


def test_task_operation_internal_helpers_cover_epic_child_resolution(tmp_path: Path) -> None:
    brainfile_path = write_brainfile(tmp_path / ".brainfile" / "brainfile.md")
    dirs = ensure_dirs(str(brainfile_path))

    epic = Task(
        id="epic-1",
        title="Epic",
        column="todo",
        type="epic",
        subtasks=[
            "task-1",
            Subtask(id="task-2", title="Second", completed=False),
            {"id": "task-3", "title": "Third"},
            "task-1",
        ],
    )
    assert _extract_epic_child_task_ids(epic) == ["task-1", "task-2", "task-3"]

    child_one = Task(id="task-1", title="One", column="todo", parent_id="epic-1")
    child_two = Task(id="task-2", title="Two", column="done")
    child_three = Task(id="task-3", title="Three", column="done")
    write_task_file(get_task_file_path(dirs.board_dir, child_one.id), child_one, compose_body("one"))
    write_task_file(get_log_file_path(dirs.logs_dir, child_two.id), child_two, compose_body("two"))
    write_task_file(get_log_file_path(dirs.logs_dir, child_three.id), child_three, compose_body("three"))

    linked_children = _resolve_child_tasks("epic-1", ["task-2", "task-3"], dirs.board_dir, dirs.logs_dir)
    assert linked_children == [{"id": "task-1", "title": "One"}]

    fallback_children = _resolve_child_tasks("epic-2", ["task-2", "task-3"], dirs.board_dir, dirs.logs_dir)
    assert fallback_children == [
        ChildTaskSummary(id="task-2", title="Two"),
        ChildTaskSummary(id="task-3", title="Three"),
    ]

    assert _build_child_tasks_section([]) == "## Child Tasks\nNo child tasks recorded."
    assert _build_child_tasks_section(fallback_children) == "## Child Tasks\n- task-2: Two\n- task-3: Three"
    assert _append_body_section("", "## Child Tasks\n- task-2: Two") == "## Child Tasks\n- task-2: Two\n"
    assert _append_body_section("Existing body\n", "## Child Tasks\n- task-2: Two") == (
        "Existing body\n\n## Child Tasks\n- task-2: Two\n"
    )


def test_ledger_helpers_cover_record_building_queries_and_context(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    task = Task(
        id="task-1",
        title="Ship auth",
        type="epic",
        column="done",
        created_at="2026-01-01T00:00:00Z",
        completed_at="2026-01-02T12:00:00Z",
        assignee="alice",
        priority="high",
        tags=["api", "api", "backend"],
        parent_id="epic-0",
        related_files=["./src/auth.py", "src/auth.py", "docs/readme.md"],
        subtasks=[
            Subtask(id="task-1-1", title="One", completed=True),
            Subtask(id="task-1-2", title="Two", completed=False),
        ],
        contract=Contract(
            status="delivered",
            deliverables=[Deliverable(path="./src/auth.py", description="Auth module")],
            constraints=["Use JWT", "Use JWT"],
            metrics=ContractMetrics(rework_count=2),
        ),
    )

    record = build_ledger_record(task, "## Notes\nImplemented auth", {"files_changed": ["./src/auth.py"]})
    assert record.id == "task-1"
    assert record.type == "epic"
    assert record.summary == "Implemented auth"
    assert record.files_changed == ["src/auth.py"]
    assert record.related_files == ["src/auth.py", "docs/readme.md"]
    assert record.deliverables == ["src/auth.py"]
    assert record.tags == ["api", "backend"]
    assert record.constraints == ["Use JWT"]
    assert record.validation_attempts == 2
    assert record.subtasks_total == 2
    assert record.subtasks_completed == 1
    assert record.cycle_time_hours == 36
    assert record.contract_status == "delivered"

    ledger_path = append_ledger_record(str(logs_dir), record)
    assert Path(ledger_path).exists()

    second = build_ledger_record(
        Task(
            id="task-2",
            title="Docs",
            created_at="2026-01-03T00:00:00Z",
            completed_at="2026-01-03T03:30:00Z",
            related_files=["docs/readme.md"],
        ),
        "Completed docs",
        {"files_changed": ["docs/readme.md"], "summary": "Docs done", "validation_attempts": 1.9},
    )
    append_ledger_record(str(logs_dir), second)

    records = read_ledger(str(logs_dir))
    assert [item.id for item in records] == ["task-1", "task-2"]

    queried = query_ledger(str(logs_dir), {"assignee": "alice", "tags": ["backend"], "files": ["src/auth.py"]})
    assert [item.id for item in queried] == ["task-1"]

    file_history = get_file_history(str(logs_dir), "src/auth.py", {"limit": 1})
    assert [item.id for item in file_history] == ["task-1"]

    context = get_task_context(
        str(logs_dir),
        ["src/auth.py"],
        ["docs/readme.md"],
        {"limit": 2},
    )
    assert [entry.record.id for entry in context] == ["task-2", "task-1"]
    assert context[0].matched_files == ["docs/readme.md"]
    assert context[1].matched_files == ["src/auth.py", "docs/readme.md"]

    assert normalize_path_value(" ./src\\auth.py ") == "src/auth.py"
    assert is_ledger_contract_status("delivered") is True
    assert is_ledger_contract_status("unknown") is False


def test_inference_and_templates_helpers() -> None:
    assert infer_type({"type": "journal"}) == "journal"
    assert infer_type({"schema": "https://brainfile.md/v1/checklist.json"}) == "checklist"
    assert infer_type({}, filename="brainfile.adr.md") == "adr"
    assert infer_type({"entries": []}) == "journal"
    assert infer_type({"items": [{"completed": True}]}) == "checklist"
    assert infer_type({}) == "board"

    assert infer_renderer("board", {"columns": []}).value == "kanban"
    assert infer_renderer("journal", {"entries": [{"timestamp": "2026-01-01"}]}).value == "timeline"
    assert infer_renderer("checklist", {"items": [{"completed": True}]}).value == "checklist"
    assert infer_renderer("collection", {"categories": []}).value == "grouped-list"
    assert infer_renderer("document", {"sections": []}).value == "document"
    assert infer_renderer("unknown", {}).value == "tree"

    template = TaskTemplate(
        id="custom",
        name="Custom",
        template=Task(
            id="",
            title="{title}",
            description="Hello {name}",
            subtasks=[Subtask(id="old-1", title="Step", completed=False)],
        ),
        variables=[TemplateVariable(name="title", description="Title", required=True)],
    )
    processed = process_template(template, {"title": "Ship it", "name": "team"})
    assert processed["title"] == "Ship it"
    assert processed["description"] == "Hello team"
    assert processed["subtasks"][0]["id"].startswith("task-")
    assert processed["subtasks"][0]["id"].endswith("-1")

    assert get_template_by_id("feature-request") is not None
    assert get_template_by_id("missing") is None
    assert set(get_all_template_ids()) == {template.id for template in BUILT_IN_TEMPLATES}
    assert generate_subtask_id("task-1", 0) == "task-1-1"
    assert generate_task_id().startswith("task-")


def test_complete_and_delete_task_file_cover_file_lifecycle(tmp_path: Path) -> None:
    brainfile_path = write_brainfile(tmp_path / ".brainfile" / "brainfile.md")
    dirs = ensure_dirs(str(brainfile_path))

    active_path = get_task_file_path(dirs.board_dir, "task-1")
    write_task_file(active_path, Task(id="task-1", title="Do work", column="todo"), compose_body("body"))

    completed = complete_task_file(
        active_path,
        dirs.logs_dir,
        summary="Finished work",
        files_changed=["./src/work.py"],
        column_history=["todo", "in-progress"],
        validation_attempts=3,
    )
    assert completed["success"] is True
    assert Path(completed["file_path"]).exists()
    assert Path(active_path).exists() is False

    ledger_records = read_ledger(dirs.logs_dir)
    assert [record.id for record in ledger_records] == ["task-1"]
    assert ledger_records[0].summary == "Finished work"
    assert ledger_records[0].files_changed == ["src/work.py"]
    assert ledger_records[0].column_history == ["todo", "in-progress"]
    assert ledger_records[0].validation_attempts == 3

    delete_path = get_task_file_path(dirs.board_dir, "task-2")
    write_task_file(delete_path, Task(id="task-2", title="Delete me", column="todo"), compose_body("body"))
    deleted = delete_task_file(delete_path)
    assert deleted["success"] is True
    assert Path(delete_path).exists() is False
