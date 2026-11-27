# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SceneCard."""

from __future__ import annotations

from abc import ABC, abstractmethod


class SceneCardInterface(ABC):
    """One scene card: the scene it plans, the beat it sits under, and its text."""

    __slots__ = ()

    @abstractmethod
    def artifact(self) -> str:
        """The artifact name the drafted scene is stored under."""

    @abstractmethod
    def structured(self) -> str:
        """The artifact name the scene is stored under after the structure pass."""

    @abstractmethod
    def dialogued(self) -> str:
        """The artifact name the scene is stored under after the dialogue pass."""

    @abstractmethod
    def revised(self) -> str:
        """The artifact name the revised scene is stored under."""
