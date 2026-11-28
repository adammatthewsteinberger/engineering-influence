# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A tool the model may call: its name, what it does and what arguments it takes."""

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

from engineering_influence.models.interfaces.tool_definition_interface import (
    ToolDefinitionInterface,
)


@dataclass(frozen=True, slots=True)
class ToolDefinition(ToolDefinitionInterface):
    """What a model is told about one tool, in a form that both providers' formats can be made from.

    The name is limited to what the providers accept (letters, digits, ``-`` and ``_``). The
    parameters are a JSON schema of type ``object``, as plain JSON, so a definition can be
    hashed and journaled.
    """

    NAME: ClassVar[re.Pattern[str]] = re.compile(r"[A-Za-z0-9_-]{1,64}")
    KINDS: ClassVar[dict[str, Callable[[Any], bool]]] = {
        "string": lambda value: isinstance(value, str),
        "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
        "number": lambda value: isinstance(value, int | float) and not isinstance(value, bool),
        "boolean": lambda value: isinstance(value, bool),
        "array": lambda value: isinstance(value, list),
        "object": lambda value: isinstance(value, Mapping),
    }

    name: str
    description: str
    parameters: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Validate the tool's name, description and input schema when it is built."""
        if not self.NAME.fullmatch(self.name):
            raise ValueError("a tool name is 1 to 64 letters, digits, - or _")
        if not self.description.strip():
            raise ValueError("a tool needs a description the model can read")
        if not isinstance(self.parameters, Mapping) or self.parameters.get("type") != "object":
            raise ValueError("a tool's parameters are a JSON schema of type object")
        try:
            json.dumps(self.parameters)
        except (TypeError, ValueError) as error:
            raise ValueError("a tool's parameters must be plain JSON") from error

    def check(self, arguments: Mapping[str, Any]) -> str:
        """An empty string if the arguments fit the schema, otherwise a sentence saying how not.

        Only the parts of JSON Schema a tool needs are read: ``required``, each property's
        ``type`` and ``enum``, and ``additionalProperties: false``.
        """
        properties = self.parameters.get("properties") or {}
        for name in self.parameters.get("required") or []:
            if name not in arguments:
                return f"missing the required argument {name!r}"
        for name, value in arguments.items():
            spec = properties.get(name)
            if spec is None:
                if self.parameters.get("additionalProperties") is False:
                    return f"unknown argument {name!r}"
                continue
            kind = spec.get("type")
            if kind in self.KINDS and not self.KINDS[kind](value):
                return f"argument {name!r} must be of type {kind}"
            if "enum" in spec and value not in spec["enum"]:
                return f"argument {name!r} must be one of {spec['enum']}"
        return ""

    def json_schema(self) -> dict[str, Any]:
        """A copy of the parameter schema, safe to give to an adapter that may reshape it."""
        copy: dict[str, Any] = json.loads(json.dumps(self.parameters))
        return copy
