# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for the PhaseState enum."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class PhaseStateInterface(Protocol):
    """The durable lifecycle of one pipeline phase."""

    @property
    def name(self) -> str:
        """The member's name."""

    @property
    def value(self) -> str:
        """The member's value."""
