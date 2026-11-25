# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CapacityExhaustedError."""

from abc import ABC


class CapacityExhaustedErrorInterface(ABC):
    """A stage cannot continue until credit or quota is restored."""

    __slots__ = ()
