# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The skill lock as a TOML file a person can read and review."""

import os
import tomllib
from pathlib import Path
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.skill_lock_store_interface import SkillLockStoreInterface
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.models.skill_lock_entry import SkillLockEntry

KEYS = frozenset({"name", "version", "sha256", "stages"})


class TomlSkillLockStore(SkillLockStoreInterface):
    """Reads and writes ``[[skill]]`` entries in a fixed, diff-friendly layout.

    Loading is strict. An unknown key, a missing one, a wrong version or an entry the model refuses
    is an error that names the entry, never something quietly dropped: a lock that is half read
    would show a model a skill in a stage a person did not approve. Saving writes the whole file to
    a temporary name and renames it over the old one, with skills in name order, so a lock is
    never left half written and two saves of the same lock give the same bytes.
    """

    HEADER = (
        "# Installed skills: prompt text a person chose, never code. Written by `ei skills`; review a change to this file like any commit.\n"
        "# A skill whose file differs from its hash is not used. A skill reaches a stage only if it is enabled for it here.\n"
    )

    def load(self, path: Path) -> SkillLock | None:
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
        unknown = sorted(set(data) - {"version", "skill"})
        if unknown:
            raise self._invalid(f"{path} has an unknown top-level key {unknown[0]!r}")
        version = data.get("version")
        if type(version) is not int or version != SkillLock.VERSION:  # True and 1.0 equal 1
            raise self._invalid(f"{path} is version {version!r}; this reads {SkillLock.VERSION}")
        entries = data.get("skill", [])
        if not isinstance(entries, list):
            raise self._invalid(f"{path} has skill entries that are not a list of tables")
        try:
            return SkillLock(
                tuple(self._entry(entry, index) for index, entry in enumerate(entries))
            )
        except ValueError as error:
            raise self._invalid(str(error)) from error

    def save(self, path: Path, lock: SkillLock) -> None:
        """Write the lock, replacing the file whole or not at all."""
        entries = sorted(lock.entries, key=lambda entry: entry.name)
        blocks = [self.HEADER, f"version = {SkillLock.VERSION}\n"] + [
            self._block(entry) for entry in entries
        ]
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text("\n".join(blocks), encoding="utf-8")
        os.replace(temporary, path)

    def _entry(self, entry: Any, index: int) -> SkillLockEntry:
        where = f"skill #{index + 1} ({entry.get('name', '?') if isinstance(entry, dict) else '?'})"
        if not isinstance(entry, dict):
            raise self._invalid(f"{where} is not a table")
        unknown = sorted(set(entry) - KEYS)
        if unknown:
            raise self._invalid(f"{where} has an unknown key {unknown[0]!r}")
        missing = sorted(KEYS - set(entry))
        if missing:
            raise self._invalid(f"{where} is missing {missing[0]!r}")
        stages = entry["stages"]
        if not isinstance(stages, list):
            raise self._invalid(f"{where} has stages that are not a list")
        try:
            return SkillLockEntry(
                name=entry["name"],
                version=entry["version"],
                sha256=entry["sha256"],
                stages=tuple(stages),
            )
        except (ValueError, TypeError) as error:
            raise self._invalid(f"{where}: {error}") from error

    def _block(self, entry: SkillLockEntry) -> str:
        stages = "[" + ", ".join(self._quote(stage) for stage in entry.stages) + "]"
        return (
            "\n".join(
                [
                    "[[skill]]",
                    f"name = {self._quote(entry.name)}",
                    f"version = {entry.version}",
                    f"sha256 = {self._quote(entry.sha256)}",
                    f"stages = {stages}",
                ]
            )
            + "\n"
        )

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
        return ApplicationError(code="SKILL_LOCK_INVALID", message=message, http_status=422)
