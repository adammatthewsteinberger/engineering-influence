# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for QualityIssue."""

from abc import ABC


class QualityIssueInterface(ABC):
    """A defect a run found and either fixed, tolerated or could not fix."""

    __slots__ = ()
