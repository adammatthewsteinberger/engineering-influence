# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The answer screen for a Fountain section: a refusal is read from action, never from dialogue."""

from engineering_influence.services.answer_screen import AnswerScreen
from engineering_influence.services.interfaces.answer_screen_interface import AnswerScreenInterface
from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)


class FountainAnswerScreen(AnswerScreenInterface):
    """A character may say "I can't" in dialogue, and that is the story, not a refusal. So a refusal is searched for
    only in the action, headings and transitions, in the opening characters of those. The length rule is the same as
    `AnswerScreen`: a section with under half the words asked for is short."""

    NON_DIALOGUE: frozenset[str] = frozenset({"action", "heading", "transition", "centered"})

    def __init__(self, parser: FountainParserInterface) -> None:
        """Remember the Fountain parser, so dialogue is not read as a refusal."""
        self._parser = parser

    def refused(self, text: str) -> bool:
        """Whether the action opens with a refusal."""
        prose = " ".join(
            line
            for block in self._parser.blocks(text)
            if block.kind in self.NON_DIALOGUE
            for line in block.lines
        )
        return AnswerScreen.REFUSAL.search(prose[: AnswerScreen.OPENING_CHARACTERS]) is not None

    def short(self, text: str, asked_words: int) -> bool:
        """Whether the section has under half the words it was asked for."""
        return len(text.split()) < asked_words * AnswerScreen.SHORT_FRACTION
