# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Checks that each installed skill is still the text a person locked."""

import hashlib
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.skill_files_interface import SkillFilesInterface
from engineering_influence.interfaces.skill_parser_interface import SkillParserInterface
from engineering_influence.models.skill import Skill
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.models.skill_lock_entry import SkillLockEntry
from engineering_influence.services.interfaces.skill_lock_verifier_interface import (
    SkillLockVerifierInterface,
)


class SkillLockVerifier(SkillLockVerifierInterface):
    """A skill is used only if its file's SHA-256 is the one in the lock.

    The bytes that were hashed are the bytes that are parsed, so a file cannot pass the check and
    then be read as something else. The hash is checked before the file is parsed at all, a
    version that disagrees with the lock is refused, and so is a stage the lock enables that the
    skill has no text for. A skill that is installed but enabled for no stage is not read by a run.
    """

    def __init__(self, files: SkillFilesInterface, parser: SkillParserInterface) -> None:
        self._files = files
        self._parser = parser

    def skill(self, entry: SkillLockEntry, folder: Path) -> Skill:
        """The skill the entry locks, or an ApplicationError (SKILL_LOCK_MISMATCH) saying how it differs."""
        found = self._inspect(entry, folder)
        if isinstance(found, str):
            raise self._mismatch(found)
        return found

    def verified(self, lock: SkillLock, folder: Path) -> tuple[Skill, ...]:
        """Every skill enabled for some stage, checked, in name order; all the problems at once if any."""
        enabled = sorted((entry for entry in lock.entries if entry.stages), key=self._name)
        results = [self._inspect(entry, folder) for entry in enabled]
        problems = [result for result in results if isinstance(result, str)]
        if problems:
            raise self._mismatch("; ".join(problems))
        return tuple(result for result in results if isinstance(result, Skill))

    def problems(self, lock: SkillLock, folder: Path) -> tuple[str, ...]:
        """What no longer matches, for every locked skill, whether or not it is enabled."""
        results = [self._inspect(entry, folder) for entry in sorted(lock.entries, key=self._name)]
        return tuple(result for result in results if isinstance(result, str))

    def _inspect(self, entry: SkillLockEntry, folder: Path) -> Skill | str:
        path = folder / f"{entry.name}.toml"
        label = f"skill {entry.name!r}"
        try:
            data = self._files.read(path)
        except ApplicationError as error:
            return error.message
        if data is None:
            return f"{label}: {path} is missing"
        if hashlib.sha256(data).hexdigest() != entry.sha256:
            return (
                f"{label}: {path.name} has changed since it was locked; read it, "
                "then lock it again with ei skills add --replace"
            )
        try:
            skill = self._parser.parse(data, entry.name)
        except ApplicationError as error:
            return error.message
        if skill.version != entry.version:
            return f"{label}: its file is version {skill.version}, but the lock has {entry.version}"
        missing = [stage for stage in entry.stages if skill.part(stage) is None]
        if missing:
            return f"{label}: the lock enables it for {missing}, which it has no text for"
        return skill

    @staticmethod
    def _name(entry: SkillLockEntry) -> str:
        return entry.name

    @staticmethod
    def _mismatch(message: str) -> ApplicationError:
        return ApplicationError(code="SKILL_LOCK_MISMATCH", message=message, http_status=503)
