# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Installs a skill into the lock, enables it for stages, and takes it out again."""

import hashlib
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.skill_files_interface import SkillFilesInterface
from engineering_influence.interfaces.skill_parser_interface import SkillParserInterface
from engineering_influence.models.skill import Skill
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.models.skill_lock_addition import SkillLockAddition
from engineering_influence.models.skill_lock_entry import SkillLockEntry
from engineering_influence.services.interfaces.skill_lock_editor_interface import (
    SkillLockEditorInterface,
)
from engineering_influence.services.interfaces.skill_lock_verifier_interface import (
    SkillLockVerifierInterface,
)


class SkillLockEditor(SkillLockEditorInterface):
    """Every change to the lock is a change a person asked for, and none of them runs anything.

    Adding reads the file once, parses it strictly, and records the SHA-256 of **those bytes**
    together with a copy of them kept beside the lock, so what is committed is what is hashed. A
    newly added skill is enabled for no stage; a person enables it for each stage on purpose. Locking
    a skill again with ``replace`` clears its stages, because new text has not been approved for
    anything yet. Enabling checks the skill against its hash first and refuses a stage the skill
    has no text for.
    """

    def __init__(
        self,
        files: SkillFilesInterface,
        parser: SkillParserInterface,
        verifier: SkillLockVerifierInterface,
    ) -> None:
        """Remember the skill files, parser and lock verifier the edits use."""
        self._files = files
        self._parser = parser
        self._verifier = verifier

    def add(self, lock: SkillLock, folder: Path, source: Path, replace: bool) -> SkillLockAddition:
        """Lock the skill in ``source`` and keep a copy in ``folder``; nothing is enabled."""
        name = source.stem
        if source.suffix != ".toml" or not Skill.NAME.fullmatch(name):
            raise self._refused(
                "SKILL_INVALID",
                "a skill file is named like plain_style.toml: lowercase letters, digits and "
                f"underscores, then .toml (not {source.name!r})",
            )
        if lock.entry(name) is not None and not replace:
            raise self._already(name)
        data = self._files.read(source)
        if data is None:
            raise self._refused("SKILL_FILE_MISSING", f"there is no file at {source}")
        added = self._locked(lock, name, data)
        destination = folder / f"{name}.toml"
        if source.resolve() != destination.resolve():
            self._files.write(destination, data, replace)
        return added

    def add_bytes(
        self, lock: SkillLock, folder: Path, name: str, data: bytes, replace: bool
    ) -> SkillLockAddition:
        """Lock a skill given as the bytes of its file and keep them in ``folder``; nothing is enabled."""
        if lock.entry(name) is not None and not replace:
            raise self._already(name)
        added = self._locked(lock, name, data)
        self._files.write(folder / f"{name}.toml", data, replace)
        return added

    def enable(self, lock: SkillLock, folder: Path, name: str, stage: str) -> SkillLock:
        """The lock with the skill enabled for the stage."""
        entry = self._entry(lock, name)
        skill = self._verifier.skill(entry, folder)
        if skill.part(stage) is None and not skill.sections:
            raise self._refused(
                "SKILL_STAGE_UNKNOWN",
                f"skill {name!r} has no text for stage {stage!r}; it has text for: "
                + ", ".join(skill.stages()),
            )
        return self._with(lock, entry.with_stage(stage), True)

    def disable(self, lock: SkillLock, name: str, stage: str) -> SkillLock:
        """The lock with the skill no longer enabled for the stage."""
        entry = self._entry(lock, name)
        if not entry.enabled_for(stage):
            raise self._refused(
                "SKILL_NOT_ENABLED", f"skill {name!r} is not enabled for stage {stage!r}"
            )
        return self._with(lock, entry.without_stage(stage), True)

    def remove(self, lock: SkillLock, folder: Path, name: str) -> SkillLock:
        """The lock without the skill, and its copy deleted from ``folder``."""
        self._entry(lock, name)
        updated = lock.without(name)
        self._files.remove(folder / f"{name}.toml")
        return updated

    def _locked(self, lock: SkillLock, name: str, data: bytes) -> SkillLockAddition:
        skill = self._parser.parse(data, name)
        entry = SkillLockEntry(name, skill.version, hashlib.sha256(data).hexdigest())
        return SkillLockAddition(self._with(lock, entry, True), skill)

    def _already(self, name: str) -> ApplicationError:
        return self._refused(
            "SKILL_ALREADY_LOCKED",
            f"a skill named {name!r} is already locked; use --replace to lock it again",
            409,
        )

    def _entry(self, lock: SkillLock, name: str) -> SkillLockEntry:
        entry = lock.entry(name)
        if entry is None:
            raise self._refused("SKILL_UNKNOWN", f"no skill named {name!r} is locked")
        return entry

    def _with(self, lock: SkillLock, entry: SkillLockEntry, replace: bool) -> SkillLock:
        try:
            return lock.with_entry(entry, replace)
        except ValueError as error:
            raise self._refused("SKILL_LOCK_INVALID", str(error)) from error

    @staticmethod
    def _refused(code: str, message: str, status: int = 422) -> ApplicationError:
        return ApplicationError(code=code, message=message, http_status=status)
