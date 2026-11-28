# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The checks a non-fiction run makes on what its stages write."""

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.stage_output_check_interface import (
    StageOutputCheckInterface,
)
from engineering_influence.models.chapter_count import ChapterCount
from engineering_influence.services.interfaces.metadata_parser_interface import (
    MetadataParserInterface,
)
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)


class NonfictionOutputChecks(StageOutputCheckInterface):
    """The outline must be readable as chapters and the metadata as a listing, because later stages walk them.

    Checking when each is written means a malformed one stops the run right there, instead of stages later
    after drafting has been paid for. The other stages write prose that nothing parses.
    """

    OUTLINE = "outline"
    METADATA = "metadata"

    def __init__(self, outlines: OutlineParserInterface, metadata: MetadataParserInterface) -> None:
        self._outlines = outlines
        self._metadata = metadata

    def check(self, stage: str, text: str, target_words: int | None) -> None:
        """Return when the answer is usable; raise an ApplicationError saying what is wrong when it is not."""
        if stage == self.OUTLINE:
            outline = self._outlines.parse(text)
            problem = ChapterCount.mismatch(target_words, outline.count())
            if problem:
                raise ApplicationError(
                    code="OUTLINE_CHAPTER_COUNT", message=problem, http_status=422
                )
        elif stage == self.METADATA:
            self._metadata.parse(text)
