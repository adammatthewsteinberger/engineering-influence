# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes a skill file that did not exist."""

import os
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.skill_sink_interface import SkillSinkInterface


class NewFileSkillSink(SkillSinkInterface):
    """Creates the file new and never through a link, so nothing that is already there is overwritten."""

    def write_new(self, path: Path, data: bytes) -> None:
        """Create the file with these bytes."""
        path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags, 0o644)
        except FileExistsError as error:
            raise ApplicationError(
                code="SKILL_TARGET_EXISTS",
                message=f"{path} already exists; choose another name with --out",
                http_status=409,
            ) from error
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
