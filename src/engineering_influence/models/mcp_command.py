# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The command that starts an MCP server."""

import posixpath
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.mcp_command_interface import McpCommandInterface


@dataclass(frozen=True, slots=True)
class McpCommand(McpCommandInterface):
    """An executable and its arguments, checked before anything is started.

    The executable is an absolute path. A launcher that downloads or chooses code on each run
    (``npx``, ``uvx``, ``docker``, ...) is refused, because what it would run cannot be hashed here:
    install the server and give the executable or script it really runs.
    """

    LAUNCHERS: ClassVar[frozenset[str]] = frozenset(
        {"npx", "pnpx", "bunx", "uvx", "pipx", "npm", "pnpm", "yarn", "docker", "podman", "env"}
    )

    argv: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.argv, tuple) or not self.argv:
            raise ValueError("a server's command is a non-empty tuple")
        if any(not isinstance(part, str) or not part for part in self.argv):
            raise ValueError("every part of a command is a non-empty string")
        if not self.argv[0].startswith("/"):
            raise ValueError("a command starts with the absolute path of its executable")
        launcher = posixpath.basename(self.argv[0])
        if launcher in self.LAUNCHERS:
            raise ValueError(
                f"{launcher} fetches code that cannot be hashed here; "
                "install the server and lock its own executable"
            )
