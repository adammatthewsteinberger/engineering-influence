# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The tools a process has, found by name."""

from collections.abc import Iterable, Sequence

from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.interfaces.tool_registry_interface import ToolRegistryInterface
from engineering_influence.models.tool_definition import ToolDefinition


class ToolRegistry(ToolRegistryInterface):
    """Built once from the tools there are. A stage reaches only the ones it names.

    Nothing is discovered at run time: a tool is in the registry because the runtime put it there.
    """

    def __init__(self, tools: Iterable[ToolInterface]) -> None:
        self._tools: dict[str, ToolInterface] = {}
        for tool in tools:
            name = tool.definition().name
            if name in self._tools:
                raise ValueError(f"two tools are named {name!r}")
            self._tools[name] = tool

    def lookup(self, name: str) -> ToolInterface | None:
        """The tool with this name, or None."""
        return self._tools.get(name)

    def definitions(self, names: Sequence[str]) -> tuple[ToolDefinition, ...]:
        """The definitions of the named tools, in that order; a ValueError if any name is unknown."""
        unknown = [name for name in names if name not in self._tools]
        if unknown:
            raise ValueError(f"no tool is registered under {', '.join(repr(n) for n in unknown)}")
        return tuple(self._tools[name].definition() for name in names)
