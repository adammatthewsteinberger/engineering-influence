# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplayEpubPackage."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplayEpubPackageInterface(ABC):
    """The members of an EPUB that holds a screenplay."""

    __slots__ = ()

    @abstractmethod
    def entries(self, script: str) -> tuple[tuple[str, bytes, bool], ...]:
        """The archive's members in order, as (name, data, stored)."""
