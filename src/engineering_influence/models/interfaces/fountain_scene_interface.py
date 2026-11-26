# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FountainScene."""

from __future__ import annotations

from abc import ABC, abstractmethod


class FountainSceneInterface(ABC):
    """A scene: its numbered heading, its notes, and the elements that follow."""

    __slots__ = ()

    @abstractmethod
    def text(self) -> str:
        """The heading and every element of the scene, one line each."""

    @abstractmethod
    def note(self, key: str) -> str | None:
        """The value of the first note with this key, or None when the scene has none."""
