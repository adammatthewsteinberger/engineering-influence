# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Puts what a run produced on disk, with the book laid out as a project."""

from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.project_files_writer_interface import (
    ProjectFilesWriterInterface,
)
from engineering_influence.models.export_summary import ExportSummary
from engineering_influence.services.interfaces.export_run_interface import ExportRunInterface
from engineering_influence.services.interfaces.read_run_interface import ReadRunInterface


class ExportRun(ExportRunInterface):
    """The book goes to the top of the folder (``books/`` and ``src/``, as the book commands expect) and every other
    artifact goes under ``run/``, with the name it has in the run.

    Reading is all it does to the run. The folder has to be new or empty; nothing is overwritten, and either every
    file is written or none is (see the writer). A run that has stored nothing is refused, so an empty folder is not
    mistaken for a book.
    """

    BOOK = "manuscript/"
    OTHER = "run/"

    def __init__(self, reader: ReadRunInterface, writer: ProjectFilesWriterInterface) -> None:
        """Remember the run reader and the writer for the project files."""
        self._reader = reader
        self._writer = writer

    def export(self, run_id: str, target: Path) -> ExportSummary:
        """Write the run's artifacts under ``target``."""
        _, names = self._reader.summary(run_id)
        if not names:
            raise ApplicationError(
                code="RUN_HAS_NO_ARTIFACTS",
                message=f"run {run_id!r} has not stored anything yet, so there is nothing to export",
                http_status=409,
            )
        files: dict[str, bytes] = {}
        book = 0
        for name in names:
            is_book = name.startswith(self.BOOK)
            path = name.removeprefix(self.BOOK) if is_book else f"{self.OTHER}{name}"
            if path in files:
                raise ApplicationError(
                    code="EXPORT_NAME_CLASH",
                    message=f"two artifacts of run {run_id!r} would be written to {path!r}",
                    http_status=500,
                )
            files[path] = self._reader.artifact(run_id, name)
            book += is_book
        self._writer.write(target, files)
        return ExportSummary(len(files), book)
