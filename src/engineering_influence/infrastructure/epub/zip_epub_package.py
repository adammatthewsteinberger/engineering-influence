# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads and writes the members of an EPUB package with zipfile."""

import zipfile
from collections.abc import Iterable
from pathlib import Path

from engineering_influence.interfaces.epub_package_interface import EpubPackageInterface


class ZipEpubPackage(EpubPackageInterface):
    """An EPUB is a ZIP archive: the mimetype entry is stored, the others deflated."""

    def read_members(self, path: Path) -> dict[str, bytes]:
        """Every member of the archive at path, in archive order, by name."""
        with zipfile.ZipFile(path) as source:
            return {info.filename: source.read(info.filename) for info in source.infolist()}

    def write_members(
        self,
        path: Path,
        entries: Iterable[tuple[str, bytes, bool]],
        date_time: tuple[int, int, int, int, int, int],
    ) -> None:
        """Write (name, data, stored) entries in order, each stamped with date_time."""
        with zipfile.ZipFile(path, "w") as target:
            for name, data, stored in entries:
                kind = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
                target.writestr(
                    zipfile.ZipInfo(name, date_time=date_time), data, compress_type=kind
                )
