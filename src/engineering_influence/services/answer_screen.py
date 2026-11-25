# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Spots a model's refusal, and a section far shorter than it was asked to be."""

import re
from typing import ClassVar

from engineering_influence.services.interfaces.answer_screen_interface import (
    AnswerScreenInterface,
)


class AnswerScreen(AnswerScreenInterface):
    """Refusals are read from the opening of the answer only; length is compared with the words asked for.

    A refusal is a model declining in its first sentences ("I can't write that", "I'm sorry, but"), so only the
    opening is searched: a chapter that mentions refusing somewhere in its middle is still prose. A section counts as
    short when it has less than ``SHORT_FRACTION`` of the words it was asked for, which catches a truncated or
    summarised section and leaves a section that runs a little under its length alone.
    """

    OPENING_CHARACTERS: ClassVar[int] = 300
    SHORT_FRACTION: ClassVar[float] = 0.5
    REFUSAL: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:i\s*(?:can(?:'|\u2019)?t|cannot|won(?:'|\u2019)?t|am\s+(?:unable|not\s+able|not\s+comfortable)"
        r"|'m\s+(?:unable|not\s+able|not\s+comfortable))|i'?m\s+sorry|i\s+must\s+decline|as\s+an\s+ai\b)",
        re.IGNORECASE,
    )

    def refused(self, text: str) -> bool:
        """Whether the answer opens by declining to write the text."""
        return self.REFUSAL.search(text[: self.OPENING_CHARACTERS]) is not None

    def short(self, text: str, asked_words: int) -> bool:
        """Whether the answer has under half the words it was asked for."""
        return len(text.split()) < asked_words * self.SHORT_FRACTION
