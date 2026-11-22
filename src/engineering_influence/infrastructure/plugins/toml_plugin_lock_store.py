# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The plugin lock as a TOML file a person can read and review."""

import os
import tomllib
from pathlib import Path
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.plugin_lock_store_interface import PluginLockStoreInterface
from engineering_influence.models.plugin_lock import PluginLock
from engineering_influence.models.plugin_lock_entry import PluginLockEntry

KEYS = frozenset({"name", "version", "sha256", "servers", "skills"})


class TomlPluginLockStore(PluginLockStoreInterface):
    """Reads and writes ``[[plugin]]`` entries, each with a ``[plugin.skills]`` table, in a fixed layout.

    Loading is strict: an unknown key, a missing one, a wrong version or an entry the model refuses
    is an error that names the entry, never something quietly dropped. Saving writes the whole file
    to a temporary name opened without following links and renames it over the old one, with plugins
    in name order, so a lock is never half written and two saves of the same lock give the same bytes.
    """

    HEADER = (
        "# Installed plugins: reviewed bundles of skills and tool server definitions. Written by `ei plugins`; review a change to this file like any commit.\n"
        "# This file is a record. A run never reads it: what a run may do is in the tool lock and the skill lock.\n"
    )

    def load(self, path: Path) -> PluginLock | None:
        """The lock at ``path``, or None when there is no file; an ApplicationError when it is unusable."""
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError) as error:
            raise self._invalid(f"cannot read {path}: {type(error).__name__}") from error
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise self._invalid(f"{path} is not valid TOML: {error}") from error
        unknown = sorted(set(data) - {"version", "plugin"})
        if unknown:
            raise self._invalid(f"{path} has an unknown top-level key {unknown[0]!r}")
        version = data.get("version")
        if type(version) is not int or version != PluginLock.VERSION:  # True and 1.0 equal 1
            raise self._invalid(f"{path} is version {version!r}; this reads {PluginLock.VERSION}")
        entries = data.get("plugin", [])
        if not isinstance(entries, list):
            raise self._invalid(f"{path} has plugin entries that are not a list of tables")
        try:
            return PluginLock(
                tuple(self._entry(entry, index) for index, entry in enumerate(entries))
            )
        except ValueError as error:
            raise self._invalid(str(error)) from error

    def save(self, path: Path, lock: PluginLock) -> None:
        """Write the lock, replacing the file whole or not at all."""
        entries = sorted(lock.entries, key=lambda entry: entry.name)
        blocks = [self.HEADER, f"version = {PluginLock.VERSION}\n"] + [
            self._block(entry) for entry in entries
        ]
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.unlink(missing_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(temporary, flags, 0o644), "w", encoding="utf-8") as handle:
            handle.write("\n".join(blocks))
        os.replace(temporary, path)

    def _entry(self, entry: Any, index: int) -> PluginLockEntry:
        where = (
            f"plugin #{index + 1} ({entry.get('name', '?') if isinstance(entry, dict) else '?'})"
        )
        if not isinstance(entry, dict):
            raise self._invalid(f"{where} is not a table")
        unknown = sorted(set(entry) - KEYS)
        if unknown:
            raise self._invalid(f"{where} has an unknown key {unknown[0]!r}")
        missing = sorted(KEYS - set(entry))
        if missing:
            raise self._invalid(f"{where} is missing {missing[0]!r}")
        servers, skills = entry["servers"], entry["skills"]
        if not isinstance(servers, list):
            raise self._invalid(f"{where} has servers that are not a list")
        if not isinstance(skills, dict):
            raise self._invalid(f"{where} has skills that are not a table of name = hash")
        try:
            return PluginLockEntry(
                name=entry["name"],
                version=entry["version"],
                sha256=entry["sha256"],
                servers=tuple(servers),
                skills=tuple(sorted(skills.items())),
            )
        except (ValueError, TypeError) as error:
            raise self._invalid(f"{where}: {error}") from error

    def _block(self, entry: PluginLockEntry) -> str:
        servers = "[" + ", ".join(self._quote(name) for name in entry.servers) + "]"
        lines = [
            "[[plugin]]",
            f"name = {self._quote(entry.name)}",
            f"version = {entry.version}",
            f"sha256 = {self._quote(entry.sha256)}",
            f"servers = {servers}",
            "",
            "[plugin.skills]",
        ]
        lines += [f"{name} = {self._quote(digest)}" for name, digest in entry.skills]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _quote(text: str) -> str:
        """A TOML basic string: quotes and backslashes escaped, control characters as \\u escapes."""
        out = []
        for char in text:
            if char in '"\\':
                out.append("\\" + char)
            elif ord(char) < 0x20 or ord(char) == 0x7F:
                out.append(f"\\u{ord(char):04x}")
            else:
                out.append(char)
        return '"' + "".join(out) + '"'

    @staticmethod
    def _invalid(message: str) -> ApplicationError:
        return ApplicationError(code="PLUGIN_LOCK_INVALID", message=message, http_status=422)
