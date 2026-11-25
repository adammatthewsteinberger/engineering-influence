# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ContinuityFinding."""

from abc import ABC, abstractmethod


class ContinuityFindingInterface(ABC):
    """One place where a chapter disagrees with the story bible."""

    __slots__ = ()

    @abstractmethod
    def render(self) -> str:
        """The finding as one line a person can act on: ``chapter 3 (name): ...``."""
