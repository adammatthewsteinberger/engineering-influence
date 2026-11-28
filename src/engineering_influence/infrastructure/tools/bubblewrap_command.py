# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Confines an MCP server with bubblewrap: a read-only system, one writable directory, no network, and no
view of the host's sockets or of the home directory."""

from pathlib import Path

from engineering_influence.infrastructure.tools.interfaces.mcp_server_sandbox_interface import (
    McpServerSandboxInterface,
)
from engineering_influence.infrastructure.tools.interfaces.sandbox_allowance_interface import (
    SandboxAllowanceInterface,
)

# The host's temporary directory is masked, not used: the server gets an empty one of its own.
PRIVATE_TMP = "/tmp"  # nosec B108


class BubblewrapCommand(McpServerSandboxInterface):
    """Fresh network, process, IPC and UTS namespaces, all capabilities dropped, and the server is killed with its
    parent. The root is read-only, but ``/run`` and ``/tmp`` are empty so host sockets are not reachable, and
    the home directory is replaced by an empty one, except the directories the server's own interpreter and
    files live in. The working directory is the one writable place.
    """

    def __init__(self, executable: str, home: Path, allowance: SandboxAllowanceInterface) -> None:
        self._executable = executable
        self._home = home
        self._allowance = allowance

    def wrap(self, command: tuple[str, ...], workdir: Path) -> tuple[str, ...]:
        place = str(workdir.resolve())
        arguments: list[str] = [
            self._executable,
            "--die-with-parent",
            "--new-session",
            "--unshare-net",
            "--unshare-pid",
            "--unshare-ipc",
            "--unshare-uts",
            "--cap-drop",
            "ALL",
            "--ro-bind",
            "/",
            "/",
            "--dev",
            "/dev",
            "--proc",
            "/proc",
            # /run, /tmp and the home directory are empty and read-only: a write anywhere but the working directory is
            # refused, and the working directory is bound back in below as the one writable place.
            "--perms",
            "0555",
            "--tmpfs",
            "/run",
            "--perms",
            "0555",
            "--tmpfs",
            PRIVATE_TMP,
            "--perms",
            "0555",
            "--tmpfs",
            str(self._home.resolve()),
        ]
        for allowed in self._allowance.paths(command, self._home):
            arguments += ["--ro-bind", str(allowed), str(allowed)]
        arguments += ["--bind", place, place, "--chdir", place, "--", *command]
        return tuple(arguments)
