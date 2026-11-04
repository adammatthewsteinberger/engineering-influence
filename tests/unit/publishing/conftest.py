"""Shared fixtures for publishing tests."""

import json
from collections.abc import Callable
from typing import Any

import pytest


def inline(value: Any) -> str:
    """Render a Python value as an inline TOML value."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{k} = {inline(v)}" for k, v in value.items()) + " }"
    if isinstance(value, list):
        return "[" + ", ".join(inline(v) for v in value) + "]"
    if isinstance(value, str):
        return json.dumps(value)
    return repr(value)


@pytest.fixture
def dump() -> Callable[[dict[str, Any]], str]:
    def render(table: dict[str, Any]) -> str:
        return "".join(f"{key} = {inline(value)}\n" for key, value in table.items())

    return render
