# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BudgetExceededError."""

from abc import ABC


class BudgetExceededErrorInterface(ABC):
    """A call that would spend more than the run's budget allows."""

    __slots__ = ()
