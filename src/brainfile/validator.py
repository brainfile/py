"""
Validator for Brainfile objects.

This module provides validation functionality for Board objects
to ensure structural integrity.

Note: Journal and other types are community extensions and not
validated by the official brainfile library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .inference import infer_type
from .models import BrainfileType


@dataclass
class ValidationError:
    """A validation error with path and message."""

    path: str
    message: str


@dataclass
class ValidationResult:
    """Result of validation."""

    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    type: str | None = None


class BrainfileValidator:
    """Validator for Brainfile objects."""

    @staticmethod
    def validate(board: Any) -> ValidationResult:
        """
        Validate a Board object.

        Args:
            board: The board to validate

        Returns:
            ValidationResult with any errors found
        """
        errors: list[ValidationError] = []

        if not board:
            errors.append(ValidationError(path="", message="Board is null or undefined"))
            return ValidationResult(valid=False, errors=errors)

        # Validate title
        if not isinstance(board.get("title") if isinstance(board, dict) else getattr(board, "title", None), str):
            errors.append(
                ValidationError(
                    path="title",
                    message="Board title must be a non-empty string",
                )
            )
        elif isinstance(board, dict):
            if not board.get("title", "").strip():
                errors.append(
                    ValidationError(
                        path="title",
                        message="Board title must be a non-empty string",
                    )
                )
        else:
            if not getattr(board, "title", "").strip():
                errors.append(
                    ValidationError(
                        path="title",
                        message="Board title must be a non-empty string",
                    )
                )

        # Get columns
        columns = board.get("columns") if isinstance(board, dict) else getattr(board, "columns", None)

        # Validate columns
        if not isinstance(columns, list):
            errors.append(
                ValidationError(
                    path="columns",
                    message="Columns must be an array",
                )
            )
        else:
            for index, column in enumerate(columns):
                column_errors = BrainfileValidator.validate_column(
                    column, f"columns[{index}]"
                )
                errors.extend(column_errors)

        # Validate rules (optional)
        rules = board.get("rules") if isinstance(board, dict) else getattr(board, "rules", None)
        if rules is not None:
            rules_errors = BrainfileValidator.validate_rules(rules, "rules")
            errors.extend(rules_errors)

        # Validate archive (optional)
        archive = board.get("archive") if isinstance(board, dict) else getattr(board, "archive", None)
        if archive is not None:
            if not isinstance(archive, list):
                errors.append(
                    ValidationError(
                        path="archive",
                        message="Archive must be an array",
                    )
                )
            else:
                for index, task in enumerate(archive):
                    task_errors = BrainfileValidator.validate_task(
                        task, f"archive[{index}]"
                    )
                    errors.extend(task_errors)

        # Validate statsConfig (optional)
        stats_config = board.get("statsConfig") if isinstance(board, dict) else getattr(board, "stats_config", None)
        if stats_config is not None:
            if not isinstance(stats_config, (dict, object)) or stats_config is None:
                errors.append(
                    ValidationError(
                        path="statsConfig",
                        message="StatsConfig must be an object",
                    )
                )
            else:
                sc_columns = stats_config.get("columns") if isinstance(stats_config, dict) else getattr(stats_config, "columns", None)
                if sc_columns is not None:
                    if not isinstance(sc_columns, list):
                        errors.append(
                            ValidationError(
                                path="statsConfig.columns",
                                message="StatsConfig columns must be an array",
                            )
                        )
                    elif len(sc_columns) > 4:
                        errors.append(
                            ValidationError(
                                path="statsConfig.columns",
                                message="StatsConfig columns must have maximum 4 items",
                            )
                        )

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    @staticmethod
    def validate_column(column: Any, path: str) -> list[ValidationError]:
        """
        Validate a Column object.

        Args:
            column: The column to validate
            path: The path for error reporting

        Returns:
            Array of validation errors
        """
        errors: list[ValidationError] = []

        if not column:
            errors.append(
                ValidationError(
                    path=path,
                    message="Column is null or undefined",
                )
            )
            return errors

        # Get id and title
        col_id = column.get("id") if isinstance(column, dict) else getattr(column, "id", None)
        col_title = column.get("title") if isinstance(column, dict) else getattr(column, "title", None)
        col_tasks = column.get("tasks") if isinstance(column, dict) else getattr(column, "tasks", None)

        # Validate id
        if not isinstance(col_id, str) or not col_id.strip():
            errors.append(
                ValidationError(
                    path=f"{path}.id",
                    message="Column id must be a non-empty string",
                )
            )

        # Validate title
        if not isinstance(col_title, str) or not col_title.strip():
            errors.append(
                ValidationError(
                    path=f"{path}.title",
                    message="Column title must be a non-empty string",
                )
            )

        # Validate tasks
        if not isinstance(col_tasks, list):
            errors.append(
                ValidationError(
                    path=f"{path}.tasks",
                    message="Column tasks must be an array",
                )
            )
        else:
            for index, task in enumerate(col_tasks):
                task_errors = BrainfileValidator.validate_task(
                    task, f"{path}.tasks[{index}]"
                )
                errors.extend(task_errors)

        return errors

    @staticmethod
    def validate_task(task: Any, path: str) -> list[ValidationError]:
        """
        Validate a Task object.

        Args:
            task: The task to validate
            path: The path for error reporting

        Returns:
            Array of validation errors
        """
        errors: list[ValidationError] = []

        if not task:
            errors.append(
                ValidationError(
                    path=path,
                    message="Task is null or undefined",
                )
            )
            return errors

        # Get fields
        task_id = task.get("id") if isinstance(task, dict) else getattr(task, "id", None)
        task_title = task.get("title") if isinstance(task, dict) else getattr(task, "title", None)
        task_priority = task.get("priority") if isinstance(task, dict) else getattr(task, "priority", None)
        task_template = task.get("template") if isinstance(task, dict) else getattr(task, "template", None)
        task_tags = task.get("tags") if isinstance(task, dict) else getattr(task, "tags", None)
        task_related_files = task.get("relatedFiles") if isinstance(task, dict) else getattr(task, "related_files", None)
        task_subtasks = task.get("subtasks") if isinstance(task, dict) else getattr(task, "subtasks", None)

        # Validate id
        if not isinstance(task_id, str) or not task_id.strip():
            errors.append(
                ValidationError(
                    path=f"{path}.id",
                    message="Task id must be a non-empty string",
                )
            )

        # Validate title
        if not isinstance(task_title, str) or not task_title.strip():
            errors.append(
                ValidationError(
                    path=f"{path}.title",
                    message="Task title must be a non-empty string",
                )
            )

        # Validate priority (optional)
        if task_priority is not None:
            valid_priorities = ["low", "medium", "high", "critical"]
            priority_value = task_priority.value if hasattr(task_priority, "value") else task_priority
            if priority_value not in valid_priorities:
                errors.append(
                    ValidationError(
                        path=f"{path}.priority",
                        message=f"Task priority must be one of: {', '.join(valid_priorities)}",
                    )
                )

        # Validate template (optional)
        if task_template is not None:
            valid_templates = ["bug", "feature", "refactor"]
            template_value = task_template.value if hasattr(task_template, "value") else task_template
            if template_value not in valid_templates:
                errors.append(
                    ValidationError(
                        path=f"{path}.template",
                        message=f"Task template must be one of: {', '.join(valid_templates)}",
                    )
                )

        # Validate tags (optional)
        if task_tags is not None and not isinstance(task_tags, list):
            errors.append(
                ValidationError(
                    path=f"{path}.tags",
                    message="Task tags must be an array",
                )
            )

        # Validate relatedFiles (optional)
        if task_related_files is not None and not isinstance(task_related_files, list):
            errors.append(
                ValidationError(
                    path=f"{path}.relatedFiles",
                    message="Task relatedFiles must be an array",
                )
            )

        # Validate subtasks (optional)
        if task_subtasks is not None:
            if not isinstance(task_subtasks, list):
                errors.append(
                    ValidationError(
                        path=f"{path}.subtasks",
                        message="Task subtasks must be an array",
                    )
                )
            else:
                for index, subtask in enumerate(task_subtasks):
                    subtask_errors = BrainfileValidator.validate_subtask(
                        subtask, f"{path}.subtasks[{index}]"
                    )
                    errors.extend(subtask_errors)

        return errors

    @staticmethod
    def validate_subtask(subtask: Any, path: str) -> list[ValidationError]:
        """
        Validate a Subtask object.

        Args:
            subtask: The subtask to validate
            path: The path for error reporting

        Returns:
            Array of validation errors
        """
        errors: list[ValidationError] = []

        if not subtask:
            errors.append(
                ValidationError(
                    path=path,
                    message="Subtask is null or undefined",
                )
            )
            return errors

        # Get fields
        subtask_id = subtask.get("id") if isinstance(subtask, dict) else getattr(subtask, "id", None)
        subtask_title = subtask.get("title") if isinstance(subtask, dict) else getattr(subtask, "title", None)
        subtask_completed = subtask.get("completed") if isinstance(subtask, dict) else getattr(subtask, "completed", None)

        # Validate id
        if not isinstance(subtask_id, str) or not subtask_id.strip():
            errors.append(
                ValidationError(
                    path=f"{path}.id",
                    message="Subtask id must be a non-empty string",
                )
            )

        # Validate title
        if not isinstance(subtask_title, str) or not subtask_title.strip():
            errors.append(
                ValidationError(
                    path=f"{path}.title",
                    message="Subtask title must be a non-empty string",
                )
            )

        # Validate completed
        if not isinstance(subtask_completed, bool):
            errors.append(
                ValidationError(
                    path=f"{path}.completed",
                    message="Subtask completed must be a boolean",
                )
            )

        return errors

    @staticmethod
    def validate_rules(rules: Any, path: str) -> list[ValidationError]:
        """
        Validate Rules object.

        Args:
            rules: The rules to validate
            path: The path for error reporting

        Returns:
            Array of validation errors
        """
        errors: list[ValidationError] = []

        if not rules:
            errors.append(
                ValidationError(
                    path=path,
                    message="Rules is null or undefined",
                )
            )
            return errors

        rule_types = ["always", "never", "prefer", "context"]

        for rule_type in rule_types:
            rule_list = rules.get(rule_type) if isinstance(rules, dict) else getattr(rules, rule_type, None)
            if rule_list is not None:
                if not isinstance(rule_list, list):
                    errors.append(
                        ValidationError(
                            path=f"{path}.{rule_type}",
                            message=f"Rules {rule_type} must be an array",
                        )
                    )
                else:
                    for index, rule in enumerate(rule_list):
                        rule_errors = BrainfileValidator.validate_rule(
                            rule, f"{path}.{rule_type}[{index}]"
                        )
                        errors.extend(rule_errors)

        return errors

    @staticmethod
    def validate_rule(rule: Any, path: str) -> list[ValidationError]:
        """
        Validate a Rule object.

        Args:
            rule: The rule to validate
            path: The path for error reporting

        Returns:
            Array of validation errors
        """
        errors: list[ValidationError] = []

        if not rule:
            errors.append(
                ValidationError(
                    path=path,
                    message="Rule is null or undefined",
                )
            )
            return errors

        # Get fields
        rule_id = rule.get("id") if isinstance(rule, dict) else getattr(rule, "id", None)
        rule_text = rule.get("rule") if isinstance(rule, dict) else getattr(rule, "rule", None)

        # Validate id
        if not isinstance(rule_id, int):
            errors.append(
                ValidationError(
                    path=f"{path}.id",
                    message="Rule id must be a number",
                )
            )

        # Validate rule
        if not isinstance(rule_text, str) or not rule_text.strip():
            errors.append(
                ValidationError(
                    path=f"{path}.rule",
                    message="Rule rule must be a non-empty string",
                )
            )

        return errors

    @staticmethod
    def validate_brainfile(data: Any, filename: str | None = None) -> ValidationResult:
        """
        Validate any brainfile object with type detection.

        Args:
            data: The brainfile data to validate
            filename: Optional filename for type inference

        Returns:
            ValidationResult with type and any errors found
        """
        if not data:
            return ValidationResult(
                valid=False,
                errors=[
                    ValidationError(
                        path="",
                        message="Data is null or undefined",
                    )
                ],
            )

        # Infer type
        detected_type = infer_type(data, filename)

        # Validate base fields (common to all types)
        errors: list[ValidationError] = []

        title = data.get("title") if isinstance(data, dict) else getattr(data, "title", None)
        if not isinstance(title, str) or not title.strip():
            errors.append(
                ValidationError(
                    path="title",
                    message="Title must be a non-empty string",
                )
            )

        # Type-specific validation
        # Official apps only support board type
        columns = data.get("columns") if isinstance(data, dict) else getattr(data, "columns", None)

        if detected_type == BrainfileType.BOARD.value or (not detected_type and columns):
            board_result = BrainfileValidator.validate(data)
            errors.extend(board_result.errors)
        # Note: Journal and other types are community extensions
        # and are not validated by the official library

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            type=detected_type,
        )
