# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for the FailureKind enum."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class FailureKindInterface(Protocol):
    """Retry a transient failure, park a run on a capacity failure, stop on anything else."""

    @property
    def name(self) -> str:
        """The member's name."""

    @property
    def value(self) -> str:
        """The member's value."""
