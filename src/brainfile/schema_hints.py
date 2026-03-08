from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

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


class SchemaHints(_ModelMixin):
    __slots__ = (
        "renderer",
        "columns_path",
        "items_path",
        "title_field",
        "status_field",
        "timestamp_field",
        "_extras",
    )

    def __init__(
        self,
        renderer: str | None = None,
        columns_path: str | None = None,
        items_path: str | None = None,
        title_field: str | None = None,
        status_field: str | None = None,
        timestamp_field: str | None = None,
    ):
        self.renderer = renderer
        self.columns_path = columns_path
        self.items_path = items_path
        self.title_field = title_field
        self.status_field = status_field
        self.timestamp_field = timestamp_field
        self._extras = {}


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


def load_schema_hints(schema_url: str) -> SchemaHints | None:
    try:
        with urllib.request.urlopen(_schema_request(schema_url), timeout=10) as response:
            if response.status != 200:
                _warn(f"Warning: Failed to load schema from {schema_url}: HTTP {response.status}")
                return None

            payload = response.read().decode("utf-8")
            return parse_schema_hints(json.loads(payload))
    except urllib.error.URLError as exc:
        _warn(f"Warning: Failed to load schema from {schema_url}: {exc}")
        return None
    except json.JSONDecodeError as exc:
        _warn(f"Warning: Invalid JSON in schema from {schema_url}: {exc}")
        return None
    except Exception as exc:
        _warn(f"Warning: Error loading schema from {schema_url}: {exc}")
        return None
