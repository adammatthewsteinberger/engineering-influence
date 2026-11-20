# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ApiGuard."""

from abc import ABC


class ApiGuardInterface(ABC):
    """FastAPI dependency: throttle by address, authenticate, then throttle by key."""

    __slots__ = ()
