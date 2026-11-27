# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a bible folder: one subfolder per kind, one Markdown file per card, and an optional bible.toml at the root."""

from pathlib import Path
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.bible_library_interface import BibleLibraryInterface
from engineering_influence.models.bible_file import BibleFile


class FilesystemBibleLibrary(BibleLibraryInterface):
    """Only `.md` cards are read, and hidden files and folders are skipped. A folder or card name the bible cannot use
    (ADR 0018) is refused rather than renamed, so the author sees the name they must change."""

    SCHEMA_FILE: ClassVar[str] = "bible.toml"
    SUFFIX: ClassVar[str] = ".md"

    def read(self, folder: Path) -> tuple[BibleFile, ...]:
        """Every card, ordered by kind and then by file name."""
        root = self._root(folder)
        files: list[BibleFile] = []
        for kind_folder in sorted(self._visible(root, directories=True)):
            for path in sorted(self._visible(kind_folder, directories=False)):
                if path.suffix == self.SUFFIX:
                    files.append(self._file(kind_folder.name, path))
        return tuple(files)

    def schema(self, folder: Path) -> str:
        """The bible.toml text, or an empty string when the folder has none."""
        path = self._root(folder) / self.SCHEMA_FILE
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def _root(self, folder: Path) -> Path:
        if not folder.is_dir():
            raise ApplicationError(
                code="BIBLE_FOLDER_MISSING",
                message=f"the bible folder {str(folder)!r} does not exist",
                http_status=422,
            )
        return folder

    @staticmethod
    def _visible(folder: Path, *, directories: bool) -> list[Path]:
        """The non-hidden subfolders (or files) of a folder."""
        return [
            path
            for path in folder.iterdir()
            if not path.name.startswith(".") and path.is_dir() == directories
        ]

    @staticmethod
    def _file(kind: str, path: Path) -> BibleFile:
        try:
            return BibleFile(kind, path.stem, path.read_text(encoding="utf-8"))
        except ValueError as error:
            raise ApplicationError(
                code="BIBLE_CARD_INVALID",
                message=f"{kind}/{path.name} cannot be a bible card: {error}",
                http_status=422,
            ) from error
