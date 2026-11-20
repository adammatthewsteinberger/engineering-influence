# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for reading and writing the members of an EPUB package."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path


class EpubPackageInterface(ABC):
    """Move the members of an EPUB between its archive file and memory."""

    __slots__ = ()

    @abstractmethod
    def read_members(self, path: Path) -> dict[str, bytes]:
        """Every member of the archive at path, in archive order, by name."""

    @abstractmethod
    def write_members(
        self,
        path: Path,
        entries: Iterable[tuple[str, bytes, bool]],
        date_time: tuple[int, int, int, int, int, int],
    ) -> None:
        """Write (name, data, stored) entries in order, each stamped with date_time.

        A stored entry is left uncompressed; the rest are deflated. The entries are consumed
        lazily, one at a time, while the archive is open.
        """
