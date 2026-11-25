# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ToolRegistry: the tools a process has, found by name, and nothing is discovered later."""

from collections.abc import Mapping
from typing import Any

import pytest

from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.interfaces.tool_registry_interface import ToolRegistryInterface
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.services.tool_registry import ToolRegistry


class Named(ToolInterface):
    def __init__(self, name: str) -> None:
        self.name = name

    def definition(self) -> ToolDefinition:
        return ToolDefinition(self.name, f"The {self.name} tool.", {"type": "object"})

    def invoke(self, arguments: Mapping[str, Any]) -> str:
        return self.name


def test_it_is_a_tool_registry() -> None:
    assert isinstance(ToolRegistry(()), ToolRegistryInterface)


def test_a_tool_is_found_by_its_name_and_only_by_its_name() -> None:
    search, fetch = Named("web_search"), Named("fetch_url")
    registry = ToolRegistry((search, fetch))
    assert registry.lookup("web_search") is search
    assert registry.lookup("fetch_url") is fetch
    assert registry.lookup("web") is None
    assert registry.lookup("") is None
    assert ToolRegistry(()).lookup("web_search") is None


def test_definitions_come_back_in_the_order_asked_for() -> None:
    registry = ToolRegistry((Named("a"), Named("b"), Named("c")))
    assert [d.name for d in registry.definitions(("c", "a"))] == ["c", "a"]
    assert registry.definitions(()) == ()


def test_an_unknown_name_is_refused_and_every_unknown_name_is_listed() -> None:
    registry = ToolRegistry((Named("a"),))
    with pytest.raises(ValueError, match="no tool is registered under 'x', 'y'"):
        registry.definitions(("x", "a", "y"))


def test_two_tools_with_one_name_are_refused() -> None:
    with pytest.raises(ValueError, match="two tools are named 'a'"):
        ToolRegistry((Named("a"), Named("a")))
