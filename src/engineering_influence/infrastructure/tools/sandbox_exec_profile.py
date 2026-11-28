# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Confines an MCP server with macOS ``sandbox-exec`` and a profile written for it."""

from pathlib import Path

from engineering_influence.infrastructure.tools.interfaces.mcp_server_sandbox_interface import (
    McpServerSandboxInterface,
)
from engineering_influence.infrastructure.tools.interfaces.sandbox_allowance_interface import (
    SandboxAllowanceInterface,
)
from engineering_influence.infrastructure.tools.sandbox_allowance import SandboxAllowance


class SandboxExecProfile(McpServerSandboxInterface):
    """No network. Writes only in the server's working directory. Reads of the home directory denied, except the
    directories the server's own interpreter and files live in.

    Reads elsewhere are allowed, because a server must load system libraries from where they are installed.
    The last matching rule wins, so the home-directory denial comes after the general read allowance, and the
    allowances after the denial. ``sandbox-exec`` is deprecated by Apple but still ships with macOS.
    """

    def __init__(self, executable: str, home: Path, allowance: SandboxAllowanceInterface) -> None:
        self._executable = executable
        self._home = home
        self._allowance = allowance

    def wrap(self, command: tuple[str, ...], workdir: Path) -> tuple[str, ...]:
        allowed = self._allowance.paths(command, self._home)
        return (self._executable, "-p", self.profile(workdir, allowed), *command)

    def profile(self, workdir: Path, allowed: tuple[Path, ...] = ()) -> str:
        """The profile text for a server whose writable directory is ``workdir``."""
        rules = [
            "(version 1)",
            "(deny default)",
            "(allow process-fork)",
            "(allow process-exec)",
            "(allow signal (target self))",
            "(allow sysctl-read)",
            "(allow mach-lookup)",
            "(allow ipc-posix*)",
            "(allow file-read*)",
            f"(deny file-read* (subpath {self._quote(str(self._home.resolve()))}))",
        ]
        rules += [f"(allow file-read* (subpath {self._quote(str(p))}))" for p in allowed]
        rules += [
            f"(deny file-read* (subpath {self._quote(str((self._home / name).resolve()))}))"
            for name in SandboxAllowance.SECRET_DIRECTORIES
        ]
        rules += [
            f"(allow file-read* (subpath {self._quote(str(workdir.resolve()))}))",
            f"(allow file-write* (subpath {self._quote(str(workdir.resolve()))}))",
            '(allow file-write-data (literal "/dev/null"))',
            "(deny network*)",
        ]
        return "\n".join(rules) + "\n"

    @staticmethod
    def _quote(path: str) -> str:
        return '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'
