# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for StoryBible."""

from abc import ABC, abstractmethod


class StoryBibleInterface(ABC):
    """The facts of a novel that every chapter has to agree with."""

    __slots__ = ()

    @abstractmethod
    def names(self) -> tuple[str, ...]:
        """Every written form of every character, folded to one case, for telling characters apart."""
