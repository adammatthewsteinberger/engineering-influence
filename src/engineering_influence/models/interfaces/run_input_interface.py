# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RunInput."""

from abc import ABC, abstractmethod


class RunInputInterface(ABC):
    """A block of text a person gave a run, to be read as evidence and never as instructions."""

    __slots__ = ()

    @abstractmethod
    def digest(self) -> str:
        """The SHA-256 of the text, as 64 lowercase hex digits."""
