# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ModelUsage."""

from abc import ABC


class ModelUsageInterface(ABC):
    """Tokens one model call consumed, as the provider reported them."""

    __slots__ = ()
