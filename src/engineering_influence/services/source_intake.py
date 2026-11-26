# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Source intake: the author's folder becomes numbered, digest-pinned entries that a run stores."""

import hashlib
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.source_library_interface import SourceLibraryInterface
from engineering_influence.models.source_entry import SourceEntry
from engineering_influence.services.interfaces.source_intake_interface import SourceIntakeInterface


class SourceIntake(SourceIntakeInterface):
    """A folder with no source files is refused, since a screenplay built from nothing is not what was asked for."""

    def __init__(self, library: SourceLibraryInterface) -> None:
        self._library = library

    def intake(self, folder: Path) -> tuple[SourceEntry, ...]:
        """The sources in order, each with the SHA-256 of its text."""
        files = self._library.read(folder)
        if not files:
            raise ApplicationError(
                code="SOURCE_EMPTY",
                message=f"the source folder {str(folder)!r} has no readable source files",
                http_status=422,
            )
        return tuple(
            SourceEntry(
                number, file.text(), hashlib.sha256(file.text().encode("utf-8")).hexdigest()
            )
            for number, file in enumerate(files, 1)
        )
