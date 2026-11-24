# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SpendSummary."""

from abc import ABC, abstractmethod


class SpendSummaryInterface(ABC):
    """What a run spent, set beside what its brief was expected to cost."""

    __slots__ = ()

    @abstractmethod
    def ratio(self) -> float | None:
        """Spent divided by the expected cost, to three places, or None when there was no estimate."""
