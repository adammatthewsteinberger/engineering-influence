# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RunBudgetV1."""

from abc import ABC


class RunBudgetV1Interface(ABC):
    """The cap, what has been spent, what in-flight calls hold, and what is left."""

    __slots__ = ()
