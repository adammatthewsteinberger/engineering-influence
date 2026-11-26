# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FountainPageEstimate."""

from __future__ import annotations

from abc import ABC, abstractmethod


class FountainPageEstimateInterface(ABC):
    """An estimate of printed pages, before a script has been rendered."""

    __slots__ = ()

    @abstractmethod
    def pages(self, text: str) -> float:
        """About how many Courier pages the script runs to."""
