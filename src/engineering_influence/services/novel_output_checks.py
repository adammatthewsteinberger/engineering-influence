# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The checks a novel run makes on what its stages write."""

from engineering_influence.interfaces.stage_output_check_interface import (
    StageOutputCheckInterface,
)
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)
from engineering_influence.services.interfaces.story_bible_parser_interface import (
    StoryBibleParserInterface,
)


class NovelOutputChecks(StageOutputCheckInterface):
    """The story bible must be readable as a bible and the outline as chapters, because later stages walk them.

    Checking when each is written means a malformed one stops the run right there, instead of stages later
    after drafting has been paid for. The brief and the beats are prose that nothing parses.
    """

    STORY_BIBLE = "story_bible"
    OUTLINE = "outline"

    def __init__(self, bibles: StoryBibleParserInterface, outlines: OutlineParserInterface) -> None:
        self._bibles = bibles
        self._outlines = outlines

    def check(self, stage: str, text: str) -> None:
        """Return when the answer is usable; raise an ApplicationError saying what is wrong when it is not."""
        if stage == self.STORY_BIBLE:
            self._bibles.parse(text)
        elif stage == self.OUTLINE:
            self._outlines.parse(text)
