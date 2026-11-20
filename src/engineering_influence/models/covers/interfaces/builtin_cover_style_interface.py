# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BuiltinCoverStyle."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from engineering_influence.models.covers.cover_style import CoverStyle


class BuiltinCoverStyleInterface(ABC):
    """Used when no plugin supplies a style for a book's slug."""

    __slots__ = ()

    @abstractmethod
    def for_book(self, meta: dict[str, Any]) -> CoverStyle:
        """Derive a style from the book's metadata; the seed comes from its title."""
