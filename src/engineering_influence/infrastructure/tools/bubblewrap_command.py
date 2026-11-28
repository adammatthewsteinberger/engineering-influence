# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Confines an MCP server with bubblewrap: a read-only system, one writable directory, no network."""

from pathlib import Path

from engineering_influence.infrastructure.tools.interfaces.mcp_server_sandbox_interface import (
    McpServerSandboxInterface,
)


class BubblewrapCommand(McpServerSandboxInterface):
    """Runs the server in fresh network and process namespaces, with the root read-only.

    Only the server's working directory is writable, and the server starts in it. The namespaces are
    not reachable from the server, and the server is killed with its parent.
    """

    def __init__(self, executable: str) -> None:
        self._executable = executable

    def wrap(self, command: tuple[str, ...], workdir: Path) -> tuple[str, ...]:
        place = str(workdir.resolve())
        return (
            self._executable,
            "--die-with-parent",
            "--unshare-net",
            "--unshare-pid",
            "--ro-bind",
            "/",
            "/",
            "--dev",
            "/dev",
            "--proc",
            "/proc",
            "--bind",
            place,
            place,
            "--chdir",
            place,
            "--",
            *command,
        )
