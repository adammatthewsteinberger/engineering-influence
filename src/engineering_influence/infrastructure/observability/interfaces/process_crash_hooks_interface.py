# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ProcessCrashHooks."""

from abc import ABC, abstractmethod


class ProcessCrashHooksInterface(ABC):
    """Install vibey_bootstrap's crash hooks exactly once."""

    __slots__ = ()

    @abstractmethod
    def install(self) -> bool:
        """Return True when this call installed the hooks, False when they already were."""
