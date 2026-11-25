# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a text file as a run input."""

import re
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.run_input_reader_interface import RunInputReaderInterface
from engineering_influence.models.run_input import RunInput


class FileRunInputReader(RunInputReaderInterface):
    """A plain ``.txt``, ``.md`` or ``.markdown`` file of UTF-8 text, read through no link.

    Nothing else is opened: not a PDF or a web page (those need an extractor and are not read here), and not
    a link, a folder or a file over 256 KiB. A leading byte-order mark is dropped and Windows and old Mac line breaks
    become ``\\n``; after that the text is held to the same rules as any input, so a file with a control or invisible
    character is refused, never cleaned. The name is the one you give or the file's name made safe.
    """

    SUFFIXES = (".txt", ".md", ".markdown")
    MAX_BYTES = 256 * 1024
    BOM = chr(0xFEFF)

    def read(self, path: Path, name: str | None) -> RunInput:
        """The file as an input."""
        if path.is_symlink() or not path.is_file():
            raise self._invalid(f"{path} is not a plain file")
        if path.suffix.lower() not in self.SUFFIXES:
            raise self._invalid(
                f"{path.name} is not a text file: only {', '.join(self.SUFFIXES)} are read"
            )
        if path.stat().st_size > self.MAX_BYTES:
            raise self._invalid(f"{path.name} is larger than {self.MAX_BYTES:,} bytes")
        try:
            raw = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as error:
            raise self._invalid(f"{path.name} is not UTF-8 text") from error
        text = raw.removeprefix(self.BOM).replace("\r\n", "\n").replace("\r", "\n").strip()
        try:
            return RunInput(name or self._name(path), text, "file")
        except ValueError as error:
            raise self._invalid(str(error)) from error

    @staticmethod
    def _name(path: Path) -> str:
        return re.sub(r"[^a-z0-9_.-]+", "-", path.stem.lower()).strip("-.")[:60]

    @staticmethod
    def _invalid(why: str) -> ApplicationError:
        return ApplicationError(code="RUN_INPUT_INVALID", message=why, http_status=422)
