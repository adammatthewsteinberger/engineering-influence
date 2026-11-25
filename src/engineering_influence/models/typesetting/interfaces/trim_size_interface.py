# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for TrimSize."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.trim_size import TrimSize


class TrimSizeInterface(ABC):
    """The trim sizes a book can be printed at, and what KDP offers at each."""

    __slots__ = ()

    @classmethod
    @abstractmethod
    def for_name(cls, name: str | None) -> TrimSize:
        """The trim size a config's ``trim_size`` names; a book that sets none is 6x9."""

    @classmethod
    @abstractmethod
    def names(cls) -> tuple[str, ...]:
        """Every trim size name, in the order they are documented."""

    @abstractmethod
    def points(self) -> tuple[float, float]:
        """Width and height in PDF points."""
