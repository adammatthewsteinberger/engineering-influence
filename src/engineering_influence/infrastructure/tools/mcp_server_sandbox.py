# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The native sandbox of this system, or none: a server is then not started at all."""

from collections.abc import Callable
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.tools.bubblewrap_command import BubblewrapCommand
from engineering_influence.infrastructure.tools.interfaces.mcp_server_sandbox_interface import (
    McpServerSandboxInterface,
)
from engineering_influence.infrastructure.tools.sandbox_allowance import SandboxAllowance
from engineering_influence.infrastructure.tools.sandbox_exec_profile import SandboxExecProfile


class McpServerSandbox(McpServerSandboxInterface):
    """``sandbox-exec`` on macOS and bubblewrap on Linux, found on the path.

    Fails closed: where neither is found, ``wrap`` refuses, so the server is never started unconfined.
    """

    def __init__(self, platform: str, locate: Callable[[str], str | None], home: Path) -> None:
        self._delegate = self._choose(platform, locate, home)

    def wrap(self, command: tuple[str, ...], workdir: Path) -> tuple[str, ...]:
        if self._delegate is None:
            raise ApplicationError(
                code="SANDBOX_UNAVAILABLE",
                message="this system has no native sandbox for MCP servers (sandbox-exec on macOS, bubblewrap on"
                " Linux), so a locked server is not started without one",
                http_status=503,
            )
        return self._delegate.wrap(command, workdir)

    @staticmethod
    def _choose(
        platform: str, locate: Callable[[str], str | None], home: Path
    ) -> McpServerSandboxInterface | None:
        if platform == "darwin":
            found = locate("sandbox-exec")
            return None if found is None else SandboxExecProfile(found, home, SandboxAllowance())
        if platform.startswith("linux"):
            found = locate("bwrap")
            return None if found is None else BubblewrapCommand(found, home, SandboxAllowance())
        return None
