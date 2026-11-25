# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SpendRequest."""

from abc import ABC


class SpendRequestInterface(ABC):
    """More budget a run asks for before its next model call can spend."""

    __slots__ = ()
