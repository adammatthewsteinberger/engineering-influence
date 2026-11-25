# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Everything an MCP server advertised, and the hash that pins it."""

import hashlib
import json
from dataclasses import dataclass

from engineering_influence.models.interfaces.mcp_tool_set_interface import McpToolSetInterface
from engineering_influence.models.mcp_tool_descriptor import McpToolDescriptor
from engineering_influence.models.tool_definition import ToolDefinition


@dataclass(frozen=True, slots=True)
class McpToolSet(McpToolSetInterface):
    """A server's whole list of tools. Its digest is what the lock file records.

    The digest covers every name, description and schema, in a fixed order, so a tool added,
    removed, renamed or reworded gives a different digest. A tool that cannot be offered to a model
    is still part of the digest: it is something the server advertises.
    """

    tools: tuple[McpToolDescriptor, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.tools, tuple):
            raise TypeError("a tool set is a tuple of tools")
        names = [tool.name for tool in self.tools]
        if len(set(names)) != len(names):
            raise ValueError("a server advertises each tool name once")

    def digest(self) -> str:
        """The SHA-256 of the canonical form of every tool, in name order."""
        canonical = [tool.canonical() for tool in sorted(self.tools, key=lambda tool: tool.name)]
        text = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def names(self) -> tuple[str, ...]:
        """The tool names, sorted."""
        return tuple(sorted(tool.name for tool in self.tools))

    def offered(self, server: str) -> tuple[ToolDefinition, ...]:
        """The definitions that can be given to a model, in name order."""
        ordered = sorted(self.tools, key=lambda tool: tool.name)
        return tuple(tool.definition(server) for tool in ordered if tool.offerable(server))

    def skipped(self, server: str) -> tuple[str, ...]:
        """The names of the tools that cannot be offered, sorted."""
        return tuple(sorted(tool.name for tool in self.tools if not tool.offerable(server)))
