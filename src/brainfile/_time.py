"""Shared timestamp utilities."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now_iso() -> str:
    """Return current UTC time as ISO-8601 string with millisecond precision and Z suffix."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
