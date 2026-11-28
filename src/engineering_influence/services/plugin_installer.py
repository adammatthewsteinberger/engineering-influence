# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Installs a plugin by locking its skills and recording its hash, and runs and contacts nothing."""

import hashlib
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.plugin_parser_interface import PluginParserInterface
from engineering_influence.interfaces.skill_files_interface import SkillFilesInterface
from engineering_influence.interfaces.skill_writer_interface import SkillWriterInterface
from engineering_influence.models.plugin_addition import PluginAddition
from engineering_influence.models.plugin_bundle import PluginBundle
from engineering_influence.models.plugin_lock import PluginLock
from engineering_influence.models.plugin_lock_entry import PluginLockEntry
from engineering_influence.models.plugin_removal import PluginRemoval
from engineering_influence.models.skill import Skill
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.services.interfaces.plugin_installer_interface import (
    PluginInstallerInterface,
)
from engineering_influence.services.interfaces.skill_lock_editor_interface import (
    SkillLockEditorInterface,
)


class PluginInstaller(PluginInstallerInterface):
    """What installing a plugin does is short and cannot be made longer by the plugin.

    It reads the file **once**, hashes those bytes and parses them strictly. Each skill in it goes
    into the skill lock through the same editor ``ei skills add`` uses, so it is enabled for no stage.
    A copy of the bundle is kept beside the plugin lock, and the plugin lock records its hash, the
    names of the servers it described and the hash each skill was locked under. **Nothing else
    happens**: no server is started or contacted (a person locks each with ``ei tools add``), no
    tool is granted and no skill is enabled for a stage. A plugin that is already installed, or
    whose skills are already locked, is refused before anything is written, because replacing
    text a person approved is a decision for ``ei plugins remove`` and then ``add`` again.
    """

    def __init__(
        self,
        files: SkillFilesInterface,
        parser: PluginParserInterface,
        writer: SkillWriterInterface,
        skills: SkillLockEditorInterface,
    ) -> None:
        """Remember the skill files, parser, writer and skill lock editor the install uses."""
        self._files = files
        self._parser = parser
        self._writer = writer
        self._skills = skills

    def inspect(self, source: Path) -> PluginBundle:
        """Read and check a plugin file and change nothing."""
        return self._read(source)[1]

    def add(
        self,
        plugins: PluginLock,
        skills: SkillLock,
        plugin_folder: Path,
        skill_folder: Path,
        source: Path,
    ) -> PluginAddition:
        """Install the plugin in ``source``: lock its skills, keep a copy, record its hash."""
        data, bundle = self._read(source)
        plugin = bundle.plugin
        if plugins.entry(plugin.name) is not None:
            raise self._refused(
                "PLUGIN_ALREADY_INSTALLED",
                f"a plugin named {plugin.name!r} is already installed; "
                f"remove it first with ei plugins remove {plugin.name}",
                409,
            )
        taken = [skill.name for skill in plugin.skills if skills.entry(skill.name) is not None]
        if taken:
            raise self._refused(
                "PLUGIN_SKILL_CONFLICT",
                f"plugin {plugin.name!r} carries skills that are already locked: {', '.join(taken)}; "
                "remove each first with ei skills remove NAME",
                409,
            )
        copy = plugin_folder / f"{plugin.name}.toml"
        self._files.write(copy, data, False)
        locked, installed = skills, []
        try:
            for skill in plugin.skills:
                rendered = self._writer.render(skill)
                locked = self._skills.add_bytes(
                    locked, skill_folder, skill.name, rendered, False
                ).lock
                installed.append((skill.name, hashlib.sha256(rendered).hexdigest()))
        except BaseException:
            self._undo(skill_folder, copy, [name for name, _ in installed], locked)
            raise
        entry = PluginLockEntry(
            plugin.name, plugin.version, bundle.sha256, plugin.server_names(), tuple(installed)
        )
        return PluginAddition(plugins.with_entry(entry), locked, bundle)

    def remove(
        self,
        plugins: PluginLock,
        skills: SkillLock,
        plugin_folder: Path,
        skill_folder: Path,
        name: str,
    ) -> PluginRemoval:
        """Take the plugin out, with the skills it installed that are still exactly what it installed."""
        entry = plugins.entry(name)
        if entry is None:
            raise self._refused("PLUGIN_UNKNOWN", f"no plugin named {name!r} is installed")
        locked, removed, kept = skills, [], []
        for skill, digest in entry.skills:
            found = locked.entry(skill)
            if found is None:
                continue
            if found.sha256 != digest:
                kept.append(skill)
                continue
            locked = self._skills.remove(locked, skill_folder, skill)
            removed.append(skill)
        self._files.remove(plugin_folder / f"{name}.toml")
        return PluginRemoval(plugins.without(name), locked, tuple(removed), tuple(kept))

    def _read(self, source: Path) -> tuple[bytes, PluginBundle]:
        name = source.stem
        if source.suffix != ".toml" or not Skill.NAME.fullmatch(name):
            raise self._refused(
                "PLUGIN_INVALID",
                "a plugin file is named like research_pack.toml: lowercase letters, digits and "
                f"underscores, then .toml (not {source.name!r})",
            )
        data = self._files.read(source)
        if data is None:
            raise self._refused("PLUGIN_FILE_MISSING", f"there is no file at {source}")
        plugin = self._parser.parse(data, name)
        return data, PluginBundle(plugin, hashlib.sha256(data).hexdigest())

    def _undo(
        self, skill_folder: Path, copy: Path, installed: list[str], locked: SkillLock
    ) -> None:
        for skill in installed:
            self._skills.remove(locked, skill_folder, skill)
        self._files.remove(copy)

    @staticmethod
    def _refused(code: str, message: str, status: int = 422) -> ApplicationError:
        return ApplicationError(code=code, message=message, http_status=status)
