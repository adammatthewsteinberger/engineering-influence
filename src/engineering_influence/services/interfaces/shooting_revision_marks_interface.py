# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ShootingRevisionMarks."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ShootingRevisionMarksInterface(ABC):
    """Marks the scenes a revision changed, against the baseline script they were revised from."""

    __slots__ = ()

    @abstractmethod
    def mark(
        self, baseline: str, script: str, revision: int, revision_date: str | None = None
    ) -> str:
        """The numbered script with each new or changed scene marked as revision `revision`, dated when a date is given."""
