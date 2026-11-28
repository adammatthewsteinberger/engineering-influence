# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: the verses of the bundled translations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.verse_ref import VerseRef


class ScriptureIndexInterface(ABC):
    """Reads verses from the translations the product ships, offline."""

    __slots__ = ()

    @abstractmethod
    def translations(self) -> tuple[str, ...]:
        """The translations available, by short name such as ``kjv``."""

    @abstractmethod
    def text(self, translation: str, refs: tuple[VerseRef, ...]) -> str | None:
        """The verses joined by a space in that translation, or None when one of them is not in it."""
