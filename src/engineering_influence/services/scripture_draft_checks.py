# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs the Scripture checker over every drafted chapter, as the drafting stage's checks."""

from collections.abc import Mapping

from engineering_influence.interfaces.draft_checks_interface import DraftChecksInterface
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.services.interfaces.scripture_checker_interface import (
    ScriptureCheckerInterface,
)


class ScriptureDraftChecks(DraftChecksInterface):
    """The chapters are numbered from one, in the order the outline gives them, for the findings' labels."""

    def __init__(self, checker: ScriptureCheckerInterface) -> None:
        self._checker = checker

    def issues(
        self, texts: Mapping[str, str], chapters: tuple[str, ...]
    ) -> tuple[QualityIssue, ...]:
        """The Scripture findings for every chapter, in chapter order."""
        found: list[QualityIssue] = []
        for number, text in enumerate(chapters, start=1):
            found.extend(self._checker.check(number, text))
        return tuple(found)
