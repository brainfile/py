"""Shared ruamel.yaml configuration."""

from __future__ import annotations

import contextlib

from ruamel.yaml import YAML


def create_yaml() -> YAML:
    """Create a configured YAML instance for brainfile parsing/serialization."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    with contextlib.suppress(Exception):
        yaml.sort_base_mapping_type_on_output = False  # type: ignore[attr-defined]
    return yaml
