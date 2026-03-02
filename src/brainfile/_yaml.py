"""Shared PyYAML configuration wrapper.

Replaces the previous ruamel.yaml dependency with stdlib-compatible PyYAML.
The ``create_yaml()`` helper is kept for backward compat but now returns a
thin wrapper around ``yaml.safe_load`` / ``yaml.dump``.
"""

from __future__ import annotations

from io import StringIO
from typing import Any

import yaml


class _YAMLWrapper:
    """Thin wrapper that mimics the subset of the ruamel.yaml YAML() API
    used by the brainfile codebase: ``.load(stream)`` and ``.dump(data, stream)``."""

    def load(self, stream: StringIO | str) -> Any:
        """Load YAML from a stream or string."""
        if isinstance(stream, StringIO):
            return yaml.safe_load(stream.read())
        return yaml.safe_load(stream)

    def dump(self, data: Any, stream: StringIO | None = None) -> str | None:
        """Dump data as YAML into *stream* (or return as string).

        Uses ``default_flow_style=False`` and ``sort_keys=False`` to match
        the previous ruamel.yaml output style.
        """
        output = yaml.dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        if stream is not None:
            stream.write(output)
            return None
        return output


def create_yaml() -> _YAMLWrapper:
    """Create a configured YAML instance for brainfile parsing/serialization."""
    return _YAMLWrapper()
