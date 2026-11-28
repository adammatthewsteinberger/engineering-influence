# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a folder of source files: Markdown and plain text, sorted by name, one level deep."""

from pathlib import Path
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.source_library_interface import SourceLibraryInterface
from engineering_influence.models.source_file import SourceFile


class FilesystemSourceLibrary(SourceLibraryInterface):
    """Only `.md` and `.txt` files are read; hidden files are skipped. A file over `MAX_BYTES` is refused, not truncated,
    so the author sees a short source, not a clipped one."""

    SUFFIXES: ClassVar[frozenset[str]] = frozenset({".md", ".txt"})
    MAX_BYTES: ClassVar[int] = 2_000_000

    def read(self, folder: Path) -> tuple[SourceFile, ...]:
        """The source files of the folder, sorted by name."""
        if not folder.is_dir():
            raise ApplicationError(
                code="SOURCE_FOLDER_MISSING",
                message=f"the source folder {str(folder)!r} does not exist",
                http_status=422,
            )
        files = sorted(
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix in self.SUFFIXES and not path.name.startswith(".")
        )
        return tuple(self._read(path) for path in files)

    def _read(self, path: Path) -> SourceFile:
        if path.stat().st_size > self.MAX_BYTES:
            raise ApplicationError(
                code="SOURCE_TOO_LARGE",
                message=f"source file {path.name!r} is over {self.MAX_BYTES} bytes; split it",
                http_status=422,
            )
        return SourceFile(path.name, path.read_text(encoding="utf-8"))
