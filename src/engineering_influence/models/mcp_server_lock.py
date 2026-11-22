# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One MCP server that has been reviewed and pinned."""

import posixpath
import re
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.mcp_server_lock_interface import (
    McpServerLockInterface,
)


@dataclass(frozen=True, slots=True)
class McpServerLock(McpServerLockInterface):
    """What a person approved: the command, the files it runs, who the server said it was, and its tools.

    - ``command`` starts with an absolute path to the executable. ``files`` is the SHA-256 of that
      executable and of every file named in its arguments (the script it runs), so changed code is
      noticed before it is started. Installed dependencies are not covered, and neither is anything
      the script fetches or reads at run time.
    - A launcher that downloads code on each run (``npx``, ``uvx``, ``docker``, ...) is refused:
      what it would run cannot be hashed here.
    - ``server_name``, ``server_version`` and ``tools_hash`` are what the server reported and
      advertised when it was added. A server that later says or advertises anything else is not
      started. ``tool_names`` is the same list in words, so a refusal can say what changed.
    - ``env`` is the names of the variables the server is given. Their values come from the
      environment at run time and are never written to the lock.
    """

    NAME: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9-]{0,31}")
    HASH: ClassVar[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")
    ENV: ClassVar[re.Pattern[str]] = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
    LAUNCHERS: ClassVar[frozenset[str]] = frozenset(
        {"npx", "pnpx", "bunx", "uvx", "pipx", "npm", "pnpm", "yarn", "docker", "podman", "env"}
    )

    name: str
    command: tuple[str, ...]
    files: tuple[tuple[str, str], ...]
    env: tuple[str, ...]
    server_name: str
    server_version: str
    tool_names: tuple[str, ...]
    tools_hash: str

    def __post_init__(self) -> None:
        if not self.NAME.fullmatch(self.name):
            raise ValueError(
                "a server's lock name is lowercase letters, digits and -, from a letter"
            )
        self._check_command()
        self._check_files()
        self._check_names()
        if not self.HASH.fullmatch(self.tools_hash):
            raise ValueError("the tools hash is a SHA-256 in lowercase hex")
        if not self.server_name.strip() or not self.server_version.strip():
            raise ValueError("a lock records the name and version the server reported")

    def file_hashes(self) -> dict[str, str]:
        """The locked files and their SHA-256, by path."""
        return dict(self.files)

    def _check_command(self) -> None:
        if not isinstance(self.command, tuple) or not self.command:
            raise ValueError("a server's command is a non-empty tuple")
        if any(not isinstance(part, str) or not part for part in self.command):
            raise ValueError("every part of a command is a non-empty string")
        if not self.command[0].startswith("/"):
            raise ValueError("a command starts with the absolute path of its executable")
        launcher = posixpath.basename(self.command[0])
        if launcher in self.LAUNCHERS:
            raise ValueError(
                f"{launcher} fetches code that cannot be hashed here; "
                "install the server and lock its own executable"
            )

    def _check_files(self) -> None:
        if not isinstance(self.files, tuple):
            raise TypeError("files are a tuple of (path, hash) pairs")
        paths = [path for path, _ in self.files]
        if len(set(paths)) != len(paths) or paths != sorted(paths):
            raise ValueError("files are sorted by path, each once")
        if any(
            not path.startswith("/") or not self.HASH.fullmatch(digest)
            for path, digest in self.files
        ):
            raise ValueError("a locked file is an absolute path with a SHA-256 in lowercase hex")
        if self.command[0] not in paths:
            raise ValueError("the executable itself is locked")

    def _check_names(self) -> None:
        for label, names in (("env", self.env), ("tool_names", self.tool_names)):
            if not isinstance(names, tuple) or len(set(names)) != len(names):
                raise ValueError(f"{label} is a tuple of names, each once")
        if any(not self.ENV.fullmatch(name) for name in self.env):
            raise ValueError("an environment variable name is capital letters, digits and _")
        if any(not name for name in self.tool_names):
            raise ValueError("a tool name is not empty")
