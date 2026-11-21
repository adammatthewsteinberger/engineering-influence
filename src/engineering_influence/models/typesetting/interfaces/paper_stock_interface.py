# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PaperStock."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.paper_stock import PaperStock


class PaperStockInterface(ABC):
    """The interior paper a book is printed on, which decides how thick the spine is."""

    __slots__ = ()

    @classmethod
    @abstractmethod
    def for_name(cls, name: str | None) -> PaperStock:
        """The paper a config's ``paper`` names; a book that sets none is on white paper."""

    @classmethod
    @abstractmethod
    def names(cls) -> tuple[str, ...]:
        """Every paper name, in the order they are documented."""
