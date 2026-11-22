# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Skill files on disk: plain files only, never followed through a link, and never large."""

import os
import stat
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.skill_files_interface import SkillFilesInterface


class DirectorySkillFiles(SkillFilesInterface):
    """Reads a skill file only if it is a regular file of at most ``MAX_BYTES``, and refuses a link.

    The file is opened without following a link and checked on the descriptor that was opened, so
    a path that is swapped for a link between a check and a read cannot send the read somewhere
    else. A dangling link is refused the same way, not reported as missing. A write goes to a
    temporary name and is renamed over the file, so a skill is never half written.
    """

    MAX_BYTES = 64 * 1024

    def read(self, path: Path) -> bytes | None:
        """The file's bytes, or None when there is no such file."""
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except FileNotFoundError:
            return None
        except OSError as error:
            raise self._unusable(path, error.strerror or type(error).__name__) from error
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise self._unusable(path, "it is not a plain file")
        with os.fdopen(descriptor, "rb") as handle:
            data = handle.read(self.MAX_BYTES + 1)
        if len(data) > self.MAX_BYTES:
            raise self._unusable(path, f"it is longer than {self.MAX_BYTES} bytes")
        return data

    def write(self, path: Path, data: bytes, replace: bool) -> None:
        """Write the file whole or not at all; an existing file is replaced only if asked."""
        if len(data) > self.MAX_BYTES:
            raise self._unusable(path, f"it is longer than {self.MAX_BYTES} bytes")
        if os.path.lexists(path) and not replace:
            raise ApplicationError(
                code="SKILL_FILE_EXISTS",
                message=f"{path} already exists; remove it, or lock the skill again with --replace",
                http_status=409,
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.unlink(missing_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(temporary, flags, 0o644), "wb") as handle:
            handle.write(data)
        os.replace(temporary, path)

    def remove(self, path: Path) -> None:
        """Delete the file; it is not an error that it is already gone."""
        path.unlink(missing_ok=True)

    @staticmethod
    def _unusable(path: Path, why: str) -> ApplicationError:
        return ApplicationError(
            code="SKILL_FILE_UNUSABLE",
            message=f"{path} cannot be used as a skill: {why}",
            http_status=422,
        )
