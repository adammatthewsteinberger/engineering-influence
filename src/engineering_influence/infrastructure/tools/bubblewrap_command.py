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
        home = str(self._home.resolve())
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
            "--tmpfs",
            "/run",
            "--tmpfs",
            PRIVATE_TMP,
            "--tmpfs",
            home,
        ]
        for allowed in self._allowance.paths(command, self._home):
            arguments += ["--ro-bind", str(allowed), str(allowed)]
        # The working directory is the one writable mount. /run, /tmp and the home directory are bubblewrap's own
        # tmpfs mounts, remounted read-only after it is bound: a remount is not recursive, so the bind stays writable,
        # and every other write under those directories, including implicitly created parents, is refused.
        arguments += ["--bind", place, place]
        arguments += ["--remount-ro", "/run", "--remount-ro", PRIVATE_TMP, "--remount-ro", home]
        arguments += ["--chdir", place, "--", *command]
        return tuple(arguments)
