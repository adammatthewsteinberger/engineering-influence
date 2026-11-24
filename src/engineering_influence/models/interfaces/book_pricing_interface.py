# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Interface for BookPricing."""

from abc import ABC, abstractmethod
from typing import Any


class BookPricingInterface(ABC):
    """What the author says the book costs, and where and when they checked."""

    __slots__ = ()

    @abstractmethod
    def entries(self) -> dict[str, Any]:
        """The ``[release.pricing]`` entries, in the order they are written."""
