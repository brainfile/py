from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .models import _ModelMixin

__all__ = ["SchemaHints", "parse_schema_hints", "load_schema_hints"]

_HINT_KEYS = {
    "renderer": "x-brainfile-renderer",
    "columns_path": "x-brainfile-columns-path",
    "items_path": "x-brainfile-items-path",
    "title_field": "x-brainfile-title-field",
    "status_field": "x-brainfile-status-field",
    "timestamp_field": "x-brainfile-timestamp-field",
}


@dataclass(slots=True)
class SchemaHints(_ModelMixin):
    renderer: str | None = None
    columns_path: str | None = None
    items_path: str | None = None
    title_field: str | None = None
    status_field: str | None = None
    timestamp_field: str | None = None
    _extras: dict[str, Any] = field(default_factory=dict, repr=False)


def _string_hint(schema: dict[str, object], key: str) -> str | None:
    value = schema.get(key)
    return value if isinstance(value, str) and value else None


def parse_schema_hints(schema: dict[str, object] | None) -> SchemaHints:
    if not isinstance(schema, dict):
        return SchemaHints()

    return SchemaHints(
        renderer=_string_hint(schema, _HINT_KEYS["renderer"]),
        columns_path=_string_hint(schema, _HINT_KEYS["columns_path"]),
        items_path=_string_hint(schema, _HINT_KEYS["items_path"]),
        title_field=_string_hint(schema, _HINT_KEYS["title_field"]),
        status_field=_string_hint(schema, _HINT_KEYS["status_field"]),
        timestamp_field=_string_hint(schema, _HINT_KEYS["timestamp_field"]),
    )


def _warn(message: str) -> None:
    print(message, file=sys.stderr)


def _schema_request(schema_url: str) -> urllib.request.Request:
    return urllib.request.Request(
        schema_url,
        headers={"Accept": "application/json", "User-Agent": "brainfile-py/0.1.0"},
    )


def _load_schema_payload(schema_url: str) -> Any:
    request = _schema_request(schema_url)
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise urllib.error.HTTPError(
                schema_url,
                response.status,
                f"HTTP {response.status}",
                response.headers,
                None,
            )
        return json.loads(response.read().decode("utf-8"))


def _schema_error_message(schema_url: str, exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"Failed to load schema: HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return f"Failed to load schema: {exc}"
    if isinstance(exc, json.JSONDecodeError):
        return f"Invalid JSON in schema: {exc}"
    return f"Error loading schema: {exc}"


def _warn_schema_load_error(schema_url: str, exc: Exception) -> None:
    _warn(f"Warning: {_schema_error_message(schema_url, exc)} from {schema_url}")


def load_schema_hints(schema_url: str) -> SchemaHints | None:
    try:
        return parse_schema_hints(_load_schema_payload(schema_url))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TypeError, ValueError, OSError) as exc:
        _warn_schema_load_error(schema_url, exc)
    return None
