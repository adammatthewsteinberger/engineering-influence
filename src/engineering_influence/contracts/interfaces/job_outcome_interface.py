# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for the JobOutcome enum."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class JobOutcomeInterface(Protocol):
    """The terminal result of processing one job."""

    @property
    def name(self) -> str:
        """The member's name."""

    @property
    def value(self) -> str:
        """The member's value."""
