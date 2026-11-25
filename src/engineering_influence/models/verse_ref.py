# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One verse of the Bible, by book code, chapter and verse."""

import re
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.verse_ref_interface import VerseRefInterface


@dataclass(frozen=True, slots=True)
class VerseRef(VerseRefInterface):
    """A verse named by its USFM book code (``JHN``, ``1SA``), chapter and verse, all positive.

    The book codes are those of the bundled translations, so a reference the bundle cannot hold is refused here rather
    than looked up and missed later.
    """

    BOOK: ClassVar[re.Pattern[str]] = re.compile(r"[1-3A-Z][A-Z0-9]{2}")

    book: str
    chapter: int
    verse: int

    def __post_init__(self) -> None:
        if not isinstance(self.book, str) or not self.BOOK.fullmatch(self.book):
            raise ValueError("a verse's book is a three-character code such as JHN or 1SA")
        if type(self.chapter) is not int or self.chapter < 1:
            raise ValueError("a chapter is a positive whole number")
        if type(self.verse) is not int or self.verse < 1:
            raise ValueError("a verse is a positive whole number")

    def label(self) -> str:
        """The verse as a reader writes it, such as ``JHN 3:16``."""
        return f"{self.book} {self.chapter}:{self.verse}"
