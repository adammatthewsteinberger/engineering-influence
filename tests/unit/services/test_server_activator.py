# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A stage starts only the locked servers its run selected and the lock grants it, each once."""

from collections.abc import Mapping
from typing import Any

import pytest

from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.services.server_activator import ServerActivator
from engineering_influence.services.tool_registry import ToolRegistry

A = "a" * 64


class Named(ToolInterface):
    def __init__(self, name: str) -> None:
        self.name = name

    def definition(self) -> ToolDefinition:
        return ToolDefinition(self.name, "A tool.", {"type": "object"})

    def invoke(self, arguments: Mapping[str, Any]) -> str:
        return self.name


class Fleet:
    """Records each start; a server's tools are its name followed by __read."""

    def __init__(self) -> None:
        self.started: list[str] = []

    def activate(self, entry: McpServerLock) -> tuple[ToolInterface, ...]:
        if entry.name in self.started:
            return ()
        self.started.append(entry.name)
        return (Named(f"{entry.name}__read"),)


def server(name: str, stages: tuple[str, ...]) -> McpServerLock:
    return McpServerLock(
        name=name,
        command=(f"/usr/bin/{name}",),
        files=((f"/usr/bin/{name}", A),),
        env=(),
        server_name=name,
        server_version="1",
        tool_names=("read",),
        tools_hash=A,
        grants=tuple((stage, ("read",)) for stage in stages),
    )


def activator(*servers: McpServerLock) -> tuple[ServerActivator, Fleet, ToolRegistry]:
    fleet = Fleet()
    registry = ToolRegistry(())
    return ServerActivator(ToolLock(servers), fleet, registry), fleet, registry  # type: ignore[arg-type]


def test_a_selected_granted_server_starts_and_its_tool_joins_the_registry() -> None:
    made, fleet, registry = activator(server("docs", ("research",)))
    made.activate("research", ("docs",))
    assert fleet.started == ["docs"]
    assert registry.lookup("docs__read") is not None


def test_a_server_the_run_did_not_select_is_never_started() -> None:
    made, fleet, registry = activator(server("docs", ("research",)), server("maps", ("research",)))
    made.activate("research", ("maps",))
    assert fleet.started == ["maps"] and registry.lookup("docs__read") is None


def test_a_server_the_stage_is_not_granted_is_never_started() -> None:
    made, fleet, _ = activator(server("docs", ("outline",)))
    made.activate("research", ("docs",))
    assert fleet.started == []


def test_no_selection_means_every_server_the_stage_is_granted() -> None:
    made, fleet, _ = activator(server("docs", ("research",)), server("maps", ("outline",)))
    made.activate("research", None)
    assert fleet.started == ["docs"]


def test_a_server_already_started_is_not_registered_twice() -> None:
    made, fleet, registry = activator(server("docs", ("research",)))
    made.activate("research", ("docs",))
    made.activate("research", ("docs",))
    assert fleet.started == ["docs"]
    assert registry.definitions(("docs__read",))[0].name == "docs__read"


def test_a_tool_name_taken_by_something_else_is_refused_before_anything_is_added() -> None:
    fleet = Fleet()
    registry = ToolRegistry((Named("docs__read"),))
    made = ServerActivator(ToolLock((server("docs", ("research",)),)), fleet, registry)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="two tools are named 'docs__read'"):
        made.activate("research", ("docs",))
