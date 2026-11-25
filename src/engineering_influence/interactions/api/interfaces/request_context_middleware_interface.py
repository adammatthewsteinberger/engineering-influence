# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RequestContextMiddleware."""

from abc import ABC


class RequestContextMiddlewareInterface(ABC):
    """Give every HTTP request one correlation id, count it, and return the id to the caller."""

    __slots__ = ()
