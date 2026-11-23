# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ExportSummary."""

from abc import ABC


class ExportSummaryInterface(ABC):
    """How many files an export wrote, and how many of them are the book."""

    __slots__ = ()
