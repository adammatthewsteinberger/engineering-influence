# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for TransientStageError."""

from abc import ABC


class TransientStageErrorInterface(ABC):
    """A stage failed in a way that trying again may fix."""

    __slots__ = ()
