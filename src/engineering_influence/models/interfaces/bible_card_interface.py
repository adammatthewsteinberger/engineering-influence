# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BibleCard."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BibleCardInterface(ABC):
    """A card as the bible holds it: its front-matter fields, its body, and the cards its body links to."""

    __slots__ = ()

    @abstractmethod
    def links(self) -> tuple[tuple[str, str], ...]:
        """Each `[[kind: id]]` in the body, as a (kind, id) pair, in the order written."""

    @abstractmethod
    def artifact(self) -> str:
        """The artifact name a run stores the card under."""

    @abstractmethod
    def encode(self) -> str:
        """The card as text a run can store and read back."""
