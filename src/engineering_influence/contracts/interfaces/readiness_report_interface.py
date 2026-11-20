# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ReadinessReport."""

from abc import ABC


class ReadinessReportInterface(ABC):
    """Ready only when every dependency check is healthy."""

    __slots__ = ()
