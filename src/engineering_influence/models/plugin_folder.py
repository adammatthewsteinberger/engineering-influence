# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A Claude Code plugin folder, read and not yet converted."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from engineering_influence.models.interfaces.plugin_folder_interface import (
    PluginFolderInterface,
)


@dataclass(frozen=True, slots=True, eq=False)
class PluginFolder(PluginFolderInterface):
    """The plugin's name and description, the MCP servers it declares, its skills' text and what was set aside.

    ``servers`` is the ``mcpServers`` table as the plugin wrote it (untrusted: the converter checks every
    field), ``skills`` are ``(folder name, SKILL.md text)`` pairs in name order, and ``set_aside`` says in a
    line each what was in the folder and is not imported (commands, agents, hooks and the like) because a bundle
    here grants nothing and runs nothing.
    """

    name: str
    description: str
    servers: Mapping[str, Any]
    skills: tuple[tuple[str, str], ...]
    set_aside: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("a plugin folder has a name")
        if not isinstance(self.description, str):
            raise TypeError("a description is text")
        if not isinstance(self.servers, Mapping) or any(
            not isinstance(key, str) or not isinstance(value, Mapping)
            for key, value in self.servers.items()
        ):
            raise TypeError("the servers are a table of tables")
        if not isinstance(self.skills, tuple) or any(
            not isinstance(pair, tuple)
            or len(pair) != 2
            or not all(isinstance(part, str) for part in pair)
            for pair in self.skills
        ):
            raise TypeError("the skills are (folder, text) pairs")
        if not isinstance(self.set_aside, tuple) or any(
            not isinstance(line, str) for line in self.set_aside
        ):
            raise TypeError("what was set aside is a tuple of lines")
