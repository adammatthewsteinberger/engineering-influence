# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for the ModelAvailability enum."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ModelAvailabilityInterface(Protocol):
    """A model is usable, or it is blocked for a reason that decides what the run does next."""

    @property
    def name(self) -> str:
        """The member's name."""

    @property
    def value(self) -> str:
        """The member's value."""
