"""
Serializer for converting Brainfile objects to markdown format.

This module provides serialization functionality for converting Board,
Journal, and other brainfile types back to markdown with YAML frontmatter.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from io import StringIO
from typing import Any

from pydantic import BaseModel
from ruamel.yaml import YAML

from .models import Board
from .models import Brainfile as BrainfileUnion


@dataclass
class SerializeOptions:
    """Options for serialization."""

    indent: int = 2
    """YAML indentation (default: 2)"""

    line_width: int = -1
    """Maximum line width, -1 for unlimited (default: -1)"""

    trailing_newline: bool = True
    """Include trailing newline (default: True)"""


def _create_yaml(options: SerializeOptions) -> YAML:
    """
    Create a configured YAML instance for serialization.

    Configures the ruamel.yaml YAML instance with appropriate settings
    for brainfile serialization, including proper indentation and
    quote preservation.

    Args:
        options: Serialization options containing indent and line_width settings

    Returns:
        Configured YAML instance ready for serialization
    """
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.preserve_quotes = True
    # mapping: spaces before keys
    # sequence: spaces before list items (-)
    # offset: spaces for content after the list item marker (-)
    yaml.indent(mapping=options.indent, sequence=options.indent * 2, offset=options.indent)

    if options.line_width > 0:
        yaml.width = options.line_width
    else:
        yaml.width = 4096  # Very large to effectively disable wrapping

    return yaml


def _model_to_dict(data: Any) -> Any:
    """
    Convert a Pydantic model to a dict, handling nested models recursively.

    Uses Pydantic's model_dump with specific options:
    - by_alias=True: Preserves camelCase field names (e.g., relatedFiles)
    - exclude_none=True: Omits None values from output
    - mode='json': Ensures Enum values are converted to their string values

    Args:
        data: The data to convert. Can be a Pydantic model, dict, list, or primitive.

    Returns:
        The converted data as a plain Python dict/list/primitive.
        Pydantic models become dicts, lists are recursively processed,
        and primitives are returned as-is.
    """
    if isinstance(data, BaseModel):
        return data.model_dump(by_alias=True, exclude_none=True, mode="json")
    elif isinstance(data, dict):
        return {k: _model_to_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_model_to_dict(item) for item in data]
    else:
        return data


class BrainfileSerializer:
    """Serializer for converting Brainfile objects to markdown format."""

    @staticmethod
    def serialize(
        data: BrainfileUnion | Board | dict[str, Any],
        options: SerializeOptions | None = None,
    ) -> str:
        """
        Serialize any Brainfile object (board, journal, etc.) to markdown format.

        The type field is automatically preserved if present in the data.

        Args:
            data: The Brainfile object to serialize (Board, Journal, dict, etc.)
            options: Serialization options

        Returns:
            Markdown string with YAML frontmatter
        """
        if options is None:
            options = SerializeOptions()

        # Convert Pydantic model to dict
        data_dict = _model_to_dict(data)

        yaml = _create_yaml(options)

        stream = StringIO()
        yaml.dump(data_dict, stream)
        yaml_content = stream.getvalue()

        result = f"---\n{yaml_content}---\n"

        if not options.trailing_newline:
            result = result.rstrip()

        return result

    @staticmethod
    def serialize_yaml_only(
        data: BrainfileUnion | Board | dict[str, Any],
        options: SerializeOptions | None = None,
    ) -> str:
        """
        Serialize any Brainfile object to YAML only (without markdown wrapper).

        Args:
            data: The Brainfile object to serialize
            options: Serialization options

        Returns:
            YAML string
        """
        if options is None:
            options = SerializeOptions()

        # Convert Pydantic model to dict
        data_dict = _model_to_dict(data)

        yaml = _create_yaml(options)

        stream = StringIO()
        yaml.dump(data_dict, stream)
        return stream.getvalue()

    @staticmethod
    def pretty_print(data: BrainfileUnion | Board | dict[str, Any]) -> str:
        """
        Pretty print any Brainfile object for debugging.

        Args:
            data: The Brainfile object to print

        Returns:
            Pretty-printed JSON string
        """
        # Convert Pydantic model to dict
        data_dict = _model_to_dict(data)

        return json.dumps(data_dict, indent=2, ensure_ascii=False)
