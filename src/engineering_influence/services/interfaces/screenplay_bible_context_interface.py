# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplayBibleContext."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplayBibleContextInterface(ABC):
    """Picks the bible cards a scene needs from what the run stored."""

    __slots__ = ()

    @abstractmethod
    def for_scene(self, run_id: str, text: str) -> str:
        """The bible cards the text names, each as its fields and body. Empty when no stored card is named."""
