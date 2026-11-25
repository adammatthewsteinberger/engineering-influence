# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for HealthStatus."""

from abc import ABC


class HealthStatusInterface(ABC):
    """Whether one dependency is usable, with a short reason when it is not."""

    __slots__ = ()
