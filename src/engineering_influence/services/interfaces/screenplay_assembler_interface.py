# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplayAssembler."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplayAssemblerInterface(ABC):
    """Joins drafted scenes, in order, into one Fountain script under its title page."""

    __slots__ = ()

    @abstractmethod
    def assemble(self, title_page: tuple[tuple[str, str], ...], scenes: tuple[str, ...]) -> str:
        """The whole script: the title page, FADE IN:, the scenes in order, FADE OUT. and THE END."""
