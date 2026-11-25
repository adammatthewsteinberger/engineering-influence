# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BookBuildError."""

from abc import ABC


class BookBuildErrorInterface(ABC):
    """A missing config or a failed LaTeX run."""

    __slots__ = ()
