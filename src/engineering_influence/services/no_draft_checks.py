# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A draft with nothing to check across its chapters."""

from collections.abc import Mapping

from engineering_influence.interfaces.draft_checks_interface import DraftChecksInterface
from engineering_influence.models.quality_issue import QualityIssue


class NoDraftChecks(DraftChecksInterface):
    """What a non-fiction draft does today: its chapters are not read against anything."""

    def issues(
        self, texts: Mapping[str, str], chapters: tuple[str, ...]
    ) -> tuple[QualityIssue, ...]:
        """No issues."""
        return ()
