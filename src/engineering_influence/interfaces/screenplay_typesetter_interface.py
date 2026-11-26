# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: typesets one LaTeX screenplay into a PDF and counts its pages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.screenplay_typeset import ScreenplayTypeset


class ScreenplayTypesetterInterface(ABC):
    """One screenplay per call. An adapter runs LaTeX; the domain never does."""

    __slots__ = ()

    @abstractmethod
    def typeset(self, tex: str) -> ScreenplayTypeset:
        """The LaTeX source typeset, with its exit status, PDF, page count and log tail."""
