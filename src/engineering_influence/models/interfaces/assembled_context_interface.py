# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for AssembledContext."""

from abc import ABC


class AssembledContextInterface(ABC):
    """A prompt that has been fitted to a token budget, and what it gave up to fit."""

    __slots__ = ()
