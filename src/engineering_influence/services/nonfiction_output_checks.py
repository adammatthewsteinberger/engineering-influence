# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The checks a non-fiction run makes on what its stages write."""

from engineering_influence.interfaces.stage_output_check_interface import (
    StageOutputCheckInterface,
)
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)


class NonfictionOutputChecks(StageOutputCheckInterface):
    """The outline must be readable as chapters, because the drafting stage walks it.

    Checking when the outline is written means a malformed outline stops the run right there, instead of
    one stage later after drafting has been paid for. The other stages write prose that nothing parses.
    """

    OUTLINE = "outline"

    def __init__(self, outlines: OutlineParserInterface) -> None:
        self._outlines = outlines

    def check(self, stage: str, text: str) -> None:
        """Return when the answer is usable; raise an ApplicationError saying what is wrong when it is not."""
        if stage == self.OUTLINE:
            self._outlines.parse(text)
