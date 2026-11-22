# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The chapters of a non-fiction book, in order, as the drafting stage will walk them."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.chapter_outline import ChapterOutline
from engineering_influence.models.interfaces.outline_interface import OutlineInterface


@dataclass(frozen=True, slots=True)
class Outline(OutlineInterface):
    """Between one and ``MAX_CHAPTERS`` chapters, numbered 1, 2, 3 and so on with no gaps.

    The numbering is what the drafting stage keys its files on (``chapter_01.md``), so it is
    checked here, once, rather than trusted by each caller.
    """

    MAX_CHAPTERS: ClassVar[int] = 50

    chapters: tuple[ChapterOutline, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.chapters, tuple) or not self.chapters:
            raise ValueError("an outline needs at least one chapter")
        if len(self.chapters) > self.MAX_CHAPTERS:
            raise ValueError(f"an outline has at most {self.MAX_CHAPTERS} chapters")
        numbers = [chapter.number for chapter in self.chapters]
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError(f"chapters are numbered 1 to {len(numbers)} in order, not {numbers}")

    def count(self) -> int:
        """How many chapters there are."""
        return len(self.chapters)

    def chapter(self, number: int) -> ChapterOutline:
        """The chapter with this number, or a ValueError when there is none."""
        if not 1 <= number <= len(self.chapters):
            raise ValueError(f"the outline has no chapter {number}")
        return self.chapters[number - 1]
