# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SpendLimits."""

from abc import ABC


class SpendLimitsInterface(ABC):
    """The most one run may be given and the most unspent budget all running books may hold at once."""

    __slots__ = ()
