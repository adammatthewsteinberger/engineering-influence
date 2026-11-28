# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplayTitleParser."""

from __future__ import annotations

from abc import ABC, abstractmethod

from engineering_influence.models.interfaces.screenplay_title_interface import (
    ScreenplayTitleInterface,
)


class ScreenplayTitleParserInterface(ABC):
    """Reads a film's title.toml."""

    __slots__ = ()

    @abstractmethod
    def parse(self, text: str) -> ScreenplayTitleInterface:
        """The title page entries the file names; a file that breaks the rules is refused."""
