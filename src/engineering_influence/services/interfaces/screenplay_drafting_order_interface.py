# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplayDraftingOrder."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplayDraftingOrderInterface(ABC):
    """The order in which the scenes of a screenplay are drafted (prompt 09)."""

    __slots__ = ()

    @abstractmethod
    def order(
        self, cards: tuple[tuple[int, str], ...], shareable: frozenset[int]
    ) -> tuple[int, ...]:
        """Card numbers in drafting order: the opening and closing images and All Is Lost first, then the rest in card
        order, then the scenes most likely to be shared."""
