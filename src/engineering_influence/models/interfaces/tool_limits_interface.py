# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolLimits."""

from abc import ABC


class ToolLimitsInterface(ABC):
    """How long, and how much memory and disk, an external build tool may use."""

    __slots__ = ()
