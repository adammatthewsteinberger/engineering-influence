# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for the BookKind enum."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class BookKindInterface(Protocol):
    """Whether a book is argued from sources or told as a story."""

    @property
    def name(self) -> str:
        """The member's name."""

    @property
    def value(self) -> str:
        """The member's value."""
