# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The tool lock as a TOML file a person can read and review."""

from pathlib import Path
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.toml_lock_file import TomlLockFile
from engineering_influence.interfaces.tool_lock_store_interface import ToolLockStoreInterface
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.tool_lock import ToolLock

REQUIRED = frozenset({"name", "server_name", "server_version", "tools_hash"})
LOCAL = frozenset({"command", "files"})
OPTIONAL = frozenset({"env", "tool_names", "grants", "url", "bearer_env"}) | LOCAL


class TomlToolLockStore(ToolLockStoreInterface):
    """Reads and writes ``[[server]]`` entries in a fixed, diff-friendly layout.

    Loading is strict. An unknown key, a missing one, a wrong version or an entry the model refuses
    is an error that names the entry, never something quietly dropped: a lock that is half read
    would start a server with less pinned than a person approved. Saving writes the whole file to
    a temporary name and renames it over the old one, with servers in name order, so a lock is
    never left half written and two saves of the same lock give the same bytes.
    """

    HEADER = (
        "# Locked MCP tool servers. Written by `ei tools add`; review a change to this file like any commit.\n"
        "# Nothing a run does changes it. A server whose files or advertised tools differ is not started.\n"
    )

    def load(self, path: Path) -> ToolLock | None:
        """The lock at ``path``, or None when there is no file; an ApplicationError when it is unusable."""
        data = TomlLockFile.read(
            path, table="server", version=ToolLock.VERSION, code="TOOL_LOCK_INVALID"
        )
        if data is None:
            return None
        entries = data.get("server", [])
        try:
            return ToolLock(
                tuple(self._server(entry, index) for index, entry in enumerate(entries))
            )
        except ValueError as error:
            raise self._invalid(str(error)) from error

    def save(self, path: Path, lock: ToolLock) -> None:
        """Write the lock, replacing the file whole or not at all."""
        servers = sorted(lock.servers, key=lambda server: server.name)
        blocks = [self.HEADER, f"version = {ToolLock.VERSION}\n"] + [
            self._block(s) for s in servers
        ]
        TomlLockFile.write(path, blocks)

    def _server(self, entry: Any, index: int) -> McpServerLock:
        where = (
            f"server #{index + 1} ({entry.get('name', '?') if isinstance(entry, dict) else '?'})"
        )
        if not isinstance(entry, dict):
            raise self._invalid(f"{where} is not a table")
        unknown = sorted(set(entry) - REQUIRED - OPTIONAL)
        if unknown:
            raise self._invalid(f"{where} has an unknown key {unknown[0]!r}")
        remote = "url" in entry
        if remote and sorted(({"command", "files", "env"}) & set(entry)):
            raise self._invalid(
                f"{where} has an address, so it cannot have a command, files or env variables"
            )
        missing = sorted((REQUIRED | (frozenset() if remote else LOCAL)) - set(entry))
        if missing:
            raise self._invalid(f"{where} is missing {missing[0]!r}")
        files = entry.get("files", {})
        if not isinstance(files, dict):
            raise self._invalid(f"{where} has files that are not a table")
        try:
            return McpServerLock(
                name=entry["name"],
                command=self._tuple(entry.get("command", [])),
                files=tuple(sorted(files.items())),
                env=self._tuple(entry.get("env", [])),
                server_name=entry["server_name"],
                server_version=entry["server_version"],
                tool_names=self._tuple(entry.get("tool_names", [])),
                tools_hash=entry["tools_hash"],
                grants=self._grants(entry.get("grants", {})),
                url=entry.get("url", ""),
                bearer_env=entry.get("bearer_env", ""),
            )
        except (ValueError, TypeError, AttributeError) as error:
            raise self._invalid(f"{where}: {error}") from error

    def _grants(self, table: Any) -> tuple[tuple[str, tuple[str, ...]], ...]:
        if not isinstance(table, dict):
            raise TypeError("grants are a table of stage = [tools]")
        return tuple(
            sorted((stage, tuple(sorted(self._tuple(tools)))) for stage, tools in table.items())
        )

    @staticmethod
    def _tuple(value: Any) -> tuple[Any, ...]:
        if not isinstance(value, list):
            raise TypeError("expected a list")
        return tuple(value)

    def _block(self, server: McpServerLock) -> str:
        where = (
            [f"url = {self._quote(server.url)}"]
            + ([f"bearer_env = {self._quote(server.bearer_env)}"] if server.bearer_env else [])
            if server.remote()
            else [
                f"command = {self._array(server.command)}",
                f"env = {self._array(server.env)}",
            ]
        )
        lines = [
            "[[server]]",
            f"name = {self._quote(server.name)}",
            *where,
            f"server_name = {self._quote(server.server_name)}",
            f"server_version = {self._quote(server.server_version)}",
            f"tool_names = {self._array(server.tool_names)}",
            f"tools_hash = {self._quote(server.tools_hash)}",
        ]
        if not server.remote():
            lines += ["", "[server.files]"]
            lines += [
                f"{self._quote(path)} = {self._quote(digest)}" for path, digest in server.files
            ]
        if server.grants:
            lines += ["", "[server.grants]"]
            lines += [f"{stage} = {self._array(tools)}" for stage, tools in server.grants]
        return "\n".join(lines) + "\n"

    def _array(self, items: tuple[str, ...]) -> str:
        return "[" + ", ".join(self._quote(item) for item in items) + "]"

    @staticmethod
    def _quote(text: str) -> str:
        """A TOML basic string."""
        return TomlLockFile.quote(text)

    @staticmethod
    def _invalid(message: str) -> ApplicationError:
        return ApplicationError(code="TOOL_LOCK_INVALID", message=message, http_status=422)
