# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How many chapters a book of a target length should have, and whether an outline has about that many."""

from typing import ClassVar

from engineering_influence.models.interfaces.chapter_count_interface import (
    ChapterCountInterface,
)


class ChapterCount(ChapterCountInterface):
    """One rule for the outline's prompt, the outline's check and the drafter, so they agree on the number.

    A book of ``target_words`` gets one chapter per ``WORDS_PER_CHAPTER`` words, rounded to the nearest whole
    chapter and kept between ``MINIMUM`` and ``MAXIMUM``. With no target the rule has no number and the model
    chooses, as it always did. An outline is accepted when its count is within ``TOLERANCE`` of that number, so a
    model that is a chapter or two out is not refused, but one that writes a third of the book is.
    """

    WORDS_PER_CHAPTER: ClassVar[int] = 3_500
    MINIMUM: ClassVar[int] = 3
    MAXIMUM: ClassVar[int] = 30
    TOLERANCE: ClassVar[float] = 0.15

    @classmethod
    def for_target(cls, target_words: int | None) -> int | None:
        """The number of chapters for the target, or None when the brief gives no target."""
        if target_words is None:
            return None
        chapters = round(target_words / cls.WORDS_PER_CHAPTER)
        return min(cls.MAXIMUM, max(cls.MINIMUM, chapters))

    @classmethod
    def mismatch(cls, target_words: int | None, chapters: int) -> str | None:
        """Why an outline of ``chapters`` chapters is the wrong size for the target, or None when it is right enough."""
        expected = cls.for_target(target_words)
        if expected is None or abs(chapters - expected) <= expected * cls.TOLERANCE:
            return None
        return (
            f"the outline has {chapters} chapters but a book of {target_words} words needs "
            f"about {expected}; write {expected} chapters, each about {cls.WORDS_PER_CHAPTER} words"
        )
