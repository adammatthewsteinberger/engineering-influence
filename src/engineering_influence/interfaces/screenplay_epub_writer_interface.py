# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: writes an EPUB's members to an archive and checks it."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplayEpubWriterInterface(ABC):
    """One archive per call. An adapter writes the file and runs the validator; the domain does neither."""

    __slots__ = ()

    @abstractmethod
    def write(self, entries: tuple[tuple[str, bytes, bool], ...]) -> tuple[bytes, tuple[str, ...]]:
        """The archive's bytes and the problems the validator found in it (none when it is valid)."""
