# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CanonCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod


class CanonCheckInterface(ABC):
    """Runs the author's own canon check, in the author's folder, and says what it printed."""

    __slots__ = ()

    @abstractmethod
    def run(self) -> tuple[int, str]:
        """The check's exit status and everything it printed, stdout and stderr together."""
