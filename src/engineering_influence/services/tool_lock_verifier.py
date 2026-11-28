# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Decides whether a locked MCP server is still the one a person approved."""

from engineering_influence.interfaces.file_hasher_interface import FileHasherInterface
from engineering_influence.models.mcp_server_info import McpServerInfo
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.mcp_tool_set import McpToolSet
from engineering_influence.services.interfaces.tool_lock_verifier_interface import (
    ToolLockVerifierInterface,
)


class ToolLockVerifier(ToolLockVerifierInterface):
    """Two checks, in the order they can be made.

    **Files, before anything is started.** Every locked file must still exist and hash the same,
    and every file named in the command (the executable and any script among its arguments) must
    be locked, so a script added to the arguments is noticed. Nothing is run to find this out.

    **The server's report, after it starts.** Its name, its version and the hash of the tools it
    advertises must match the lock; when the tools differ, the refusal names the ones added and
    removed. The names a server uses are its own words, so they are quoted.

    Each problem is one sentence. An empty result means the server is as it was approved. This
    does not cover installed dependencies, or what a script fetches or reads when it runs, and
    the file is checked before it is started, not at the moment it is run.
    """

    LIST_LIMIT = 8

    def __init__(self, hasher: FileHasherInterface) -> None:
        """Remember the file hasher the lock is verified with."""
        self._hasher = hasher

    def check_files(self, entry: McpServerLock) -> tuple[str, ...]:
        """What is wrong with the files the command would run; empty when they are as locked.

        A remote server has no files to hash, so there is nothing to find wrong before it is contacted.
        """
        if entry.remote():
            return ()
        problems: list[str] = []
        locked = entry.file_hashes()
        for path, expected in locked.items():
            actual = self._hasher.digest(path)
            if actual is None:
                problems.append(f"{path} is missing or is not a regular file")
            elif actual != expected:
                problems.append(f"{path} has changed since it was locked")
        named = [entry.command[0]] + [
            argument for argument in entry.command[1:] if self._hasher.digest(argument) is not None
        ]
        problems.extend(
            f"{path} is named in the command but is not locked"
            for path in named
            if path not in locked
        )
        return tuple(problems)

    def check_server(
        self, entry: McpServerLock, info: McpServerInfo, tools: McpToolSet
    ) -> tuple[str, ...]:
        """What differs between the lock and what the running server reports; empty when nothing."""
        problems: list[str] = []
        if info.name != entry.server_name:
            problems.append(f"the server now calls itself {info.name!r}, not {entry.server_name!r}")
        if info.version != entry.server_version:
            problems.append(
                f"the server is now version {info.version!r}, not {entry.server_version!r}"
            )
        if tools.digest() != entry.tools_hash:
            problems.append(
                "the tools the server advertises have changed" + self._difference(entry, tools)
            )
        return tuple(problems)

    def check(
        self, entry: McpServerLock, info: McpServerInfo, tools: McpToolSet
    ) -> tuple[str, ...]:
        """The problems with the files and with the server's report, together."""
        return self.check_files(entry) + self.check_server(entry, info, tools)

    def _difference(self, entry: McpServerLock, tools: McpToolSet) -> str:
        locked, now = set(entry.tool_names), set(tools.names())
        parts = []
        if now - locked:
            parts.append(f"added {self._listed(now - locked)}")
        if locked - now:
            parts.append(f"removed {self._listed(locked - now)}")
        if not parts:
            parts.append("a description or schema was reworded")
        return " (" + "; ".join(parts) + ")"

    def _listed(self, names: set[str]) -> str:
        ordered = sorted(names)
        shown = ", ".join(repr(name[:60]) for name in ordered[: self.LIST_LIMIT])
        more = len(ordered) - self.LIST_LIMIT
        return shown + (f" and {more} more" if more > 0 else "")
