# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CostEstimate."""

from abc import ABC, abstractmethod


class CostEstimateInterface(ABC):
    """What a book is expected to cost, stage by stage, before it is written."""

    __slots__ = ()

    @abstractmethod
    def essential(self) -> int:
        """The expected cost of the stages without which the book cannot be finished, in micro-dollars."""
