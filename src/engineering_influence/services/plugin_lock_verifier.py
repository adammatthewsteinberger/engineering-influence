# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Checks that each installed plugin is still the bundle a person reviewed."""

import hashlib
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.plugin_parser_interface import PluginParserInterface
from engineering_influence.interfaces.skill_files_interface import SkillFilesInterface
from engineering_influence.models.plugin_lock import PluginLock
from engineering_influence.models.plugin_lock_entry import PluginLockEntry
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.services.interfaces.plugin_lock_verifier_interface import (
    PluginLockVerifierInterface,
)


class PluginLockVerifier(PluginLockVerifierInterface):
    """The kept copy of each bundle must still have its hash and still be a valid plugin at its version.

    The skills a plugin installed are checked against the skill lock: each must still be locked, under
    the hash the plugin installed it with. A skill locked again with other text is reported, because
    the plugin lock no longer describes what is in the skill lock. The servers a plugin described are
    not checked: it installed none of them.
    """

    def __init__(self, files: SkillFilesInterface, parser: PluginParserInterface) -> None:
        """Remember the skill files and parser the lock is verified with."""
        self._files = files
        self._parser = parser

    def problems(self, plugins: PluginLock, skills: SkillLock, folder: Path) -> tuple[str, ...]:
        """What no longer matches, for every installed plugin, in name order."""
        found: list[str] = []
        for entry in sorted(plugins.entries, key=lambda item: item.name):
            found.extend(self._bundle(entry, folder))
            found.extend(self._skills(entry, skills))
        return tuple(found)

    def _bundle(self, entry: PluginLockEntry, folder: Path) -> list[str]:
        path = folder / f"{entry.name}.toml"
        label = f"plugin {entry.name!r}"
        try:
            data = self._files.read(path)
        except ApplicationError as error:
            return [error.message]
        if data is None:
            return [f"{label}: {path} is missing"]
        if hashlib.sha256(data).hexdigest() != entry.sha256:
            return [f"{label}: {path.name} has changed since it was installed"]
        try:
            plugin = self._parser.parse(data, entry.name)
        except ApplicationError as error:
            return [error.message]
        if plugin.version != entry.version:
            return [
                f"{label}: its file is version {plugin.version}, but the lock has {entry.version}"
            ]
        return []

    @staticmethod
    def _skills(entry: PluginLockEntry, skills: SkillLock) -> list[str]:
        found = []
        for name, digest in entry.skills:
            locked = skills.entry(name)
            if locked is None:
                found.append(f"plugin {entry.name!r}: its skill {name!r} is no longer locked")
            elif locked.sha256 != digest:
                found.append(
                    f"plugin {entry.name!r}: its skill {name!r} was locked again with different text"
                )
        return found
