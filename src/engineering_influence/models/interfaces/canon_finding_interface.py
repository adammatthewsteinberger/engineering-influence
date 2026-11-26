# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CanonFinding."""

from __future__ import annotations

from abc import ABC, abstractmethod


class CanonFindingInterface(ABC):
    """One finding of the author's canon check."""

    __slots__ = ()

    @abstractmethod
    def is_error(self) -> bool:
        """True for an ERROR finding, False for a WARN finding."""
