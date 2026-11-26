# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes a screenplay EPUB to a scratch folder, checks it with epubcheck, and returns its bytes."""

import tempfile
from pathlib import Path
from typing import ClassVar

from engineering_influence.interfaces.epub_package_interface import EpubPackageInterface
from engineering_influence.interfaces.epubcheck_interface import EpubcheckInterface
from engineering_influence.interfaces.screenplay_epub_writer_interface import (
    ScreenplayEpubWriterInterface,
)


class TemporaryScreenplayEpubWriter(ScreenplayEpubWriterInterface):
    """The archive's members are stamped with a fixed date, so the same script always gives the same file. The scratch
    folder is removed afterwards; only the bytes and epubcheck's findings leave it."""

    NAME: ClassVar[str] = "screenplay.epub"
    DATE_TIME: ClassVar[tuple[int, int, int, int, int, int]] = (2000, 1, 1, 0, 0, 0)

    def __init__(self, package: EpubPackageInterface, validator: EpubcheckInterface) -> None:
        self._package = package
        self._validator = validator

    def write(self, entries: tuple[tuple[str, bytes, bool], ...]) -> tuple[bytes, tuple[str, ...]]:
        with tempfile.TemporaryDirectory(prefix="screenplay-epub-") as scratch:
            path = Path(scratch) / self.NAME
            self._package.write_members(path, entries, self.DATE_TIME)
            problems = tuple(self._validator.run(path))
            return path.read_bytes(), problems
