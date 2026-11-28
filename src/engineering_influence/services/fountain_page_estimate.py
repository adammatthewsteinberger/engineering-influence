# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An estimate of Courier pages for a Fountain script, used before it is rendered."""

from typing import ClassVar

from engineering_influence.services.interfaces.fountain_page_estimate_interface import (
    FountainPageEstimateInterface,
)
from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)


class FountainPageEstimate(FountainPageEstimateInterface):
    """Standard Courier: action 61 characters wide, dialogue 35, parentheticals 26, 55 lines a page, and a blank line
    after each element. The title page is not counted. The rendered PDF is the true count; this is for drafting."""

    LINES_PER_PAGE: ClassVar[int] = 55
    WIDTH: ClassVar[dict[str, int]] = {"dialogue": 35, "parenthetical": 26}
    ACTION_WIDTH: ClassVar[int] = 61

    def __init__(self, parser: FountainParserInterface) -> None:
        """Remember the Fountain parser the page estimate reads."""
        self._parser = parser

    def lines(self, text: str) -> int:
        """The script's lines, exact, so that a part of a script can be placed by summing its parts."""
        lines = 0
        for block in self._parser.blocks(text):
            if block.kind == "cue":
                lines += 1
            else:
                width = self.WIDTH.get(block.kind, self.ACTION_WIDTH)
                lines += sum(self._wrapped(line, width) for line in block.lines)
            lines += 1
        return lines

    def pages(self, text: str) -> float:
        """About how many pages the script runs to, to one decimal place."""
        return round(self.lines(text) / self.LINES_PER_PAGE, 1)

    @staticmethod
    def _wrapped(text: str, width: int) -> int:
        """How many lines the text takes at the given width, breaking between words."""
        lines, current = 1, 0
        for word in text.split():
            if current and current + 1 + len(word) > width:
                lines, current = lines + 1, len(word)
            else:
                current += (1 if current else 0) + len(word)
        return lines
