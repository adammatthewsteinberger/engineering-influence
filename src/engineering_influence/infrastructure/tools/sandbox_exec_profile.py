# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Confines an MCP server with macOS ``sandbox-exec`` and a profile written for it."""

from pathlib import Path

from engineering_influence.infrastructure.tools.interfaces.mcp_server_sandbox_interface import (
    McpServerSandboxInterface,
)


class SandboxExecProfile(McpServerSandboxInterface):
    """Denies the network, lets the server write only under its working directory, and keeps it out of
    the directories where credentials are kept.

    Reads are allowed everywhere else, because a server must load its own libraries from wherever they
    were installed. The profile is the policy: the last matching rule wins, so the secret directories are
    denied after reads are allowed. ``sandbox-exec`` is deprecated by Apple but still ships with macOS.
    """

    SECRET_DIRECTORIES = (".ssh", ".aws", ".gnupg", ".kube", ".config/gcloud")

    def __init__(self, executable: str, home: Path) -> None:
        self._executable = executable
        self._home = home

    def wrap(self, command: tuple[str, ...], workdir: Path) -> tuple[str, ...]:
        return (self._executable, "-p", self.profile(workdir), *command)

    def profile(self, workdir: Path) -> str:
        """The profile text for a server whose writable directory is ``workdir``."""
        writable = self._quote(str(workdir.resolve()))
        rules = [
            "(version 1)",
            "(deny default)",
            "(allow process*)",
            "(allow signal (target self))",
            "(allow sysctl-read)",
            "(allow mach-lookup)",
            "(allow ipc-posix*)",
            "(allow file-read*)",
            f"(allow file-write* (subpath {writable}))",
            '(allow file-write-data (literal "/dev/null"))',
        ]
        rules += [
            f"(deny file-read* (subpath {self._quote(str((self._home / name).resolve()))}))"
            for name in self.SECRET_DIRECTORIES
        ]
        rules.append("(deny network*)")
        return "\n".join(rules) + "\n"

    @staticmethod
    def _quote(path: str) -> str:
        return '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'
