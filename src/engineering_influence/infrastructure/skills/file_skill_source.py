# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a SKILL.md from a file or from the folder that holds it."""

from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.skill_source_interface import SkillSourceInterface


class FileSkillSource(SkillSourceInterface):
    """A folder means the ``SKILL.md`` in it. Anything but a plain file of UTF-8 text up to 256 KiB is refused.

    A link is never followed, so a path cannot be used to read a file somewhere else, and nothing else in
    the folder (scripts, other references) is read or run.
    """

    MAX_BYTES = 256 * 1024
    NAME = "SKILL.md"

    def read(self, path: Path) -> str:
        """The text of the file."""
        target = path / self.NAME if path.is_dir() and not path.is_symlink() else path
        if target.is_symlink() or not target.is_file():
            raise self._invalid(f"{path} is not a SKILL.md file or a folder that holds one")
        if target.stat().st_size > self.MAX_BYTES:
            raise self._invalid(f"{target} is larger than {self.MAX_BYTES} bytes")
        try:
            return target.read_bytes().decode("utf-8")
        except UnicodeDecodeError as error:
            raise self._invalid(f"{target} is not UTF-8 text") from error

    @staticmethod
    def _invalid(why: str) -> ApplicationError:
        return ApplicationError(code="SKILL_SOURCE_INVALID", message=why, http_status=422)
