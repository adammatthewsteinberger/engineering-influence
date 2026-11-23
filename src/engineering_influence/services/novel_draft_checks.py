# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a novel's drafted chapters against its story bible."""

from collections.abc import Mapping

from engineering_influence.interfaces.draft_checks_interface import DraftChecksInterface
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.services.interfaces.continuity_checker_interface import (
    ContinuityCheckerInterface,
)
from engineering_influence.services.interfaces.story_bible_parser_interface import (
    StoryBibleParserInterface,
)


class NovelDraftChecks(DraftChecksInterface):
    """Every finding of the continuity checker becomes one issue that does not block the run.

    A finding is a question, not a verdict: a flashback, or a new character named like an old one, is a good
    reason for one to be wrong. So the draft is never stopped for one, and each is recorded for the person to
    judge. The code names the kind (``CONTINUITY_NAME``, ``CONTINUITY_PLACE``, ``CONTINUITY_AGE`` and
    ``CONTINUITY_TIMELINE``) and the detail says which chapter and what to compare.
    """

    STAGE = "draft"
    BIBLE = "story_bible"

    def __init__(
        self, bibles: StoryBibleParserInterface, continuity: ContinuityCheckerInterface
    ) -> None:
        self._bibles = bibles
        self._continuity = continuity

    def issues(
        self, texts: Mapping[str, str], chapters: tuple[str, ...]
    ) -> tuple[QualityIssue, ...]:
        """The continuity findings for the whole draft, as non-blocking issues."""
        found = self._continuity.check(self._bibles.parse(texts[self.BIBLE]), chapters)
        return tuple(
            QualityIssue(self.STAGE, f"CONTINUITY_{item.kind.upper()}", item.render())
            for item in found
        )
