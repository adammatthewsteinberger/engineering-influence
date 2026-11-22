# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Guidance."""

from abc import ABC, abstractmethod


class GuidanceInterface(ABC):
    """The installed text a stage's prompt carries, and the name that goes in the journal key."""

    __slots__ = ()

    @abstractmethod
    def empty(self) -> bool:
        """Whether there is nothing to add to the prompt."""
