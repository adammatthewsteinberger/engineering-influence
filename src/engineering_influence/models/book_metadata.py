# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The listing of a book: its title, subtitle, description, seven keywords and up to three categories."""

import unicodedata
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.book_metadata_interface import BookMetadataInterface


@dataclass(frozen=True, slots=True)
class BookMetadata(BookMetadataInterface):
    """What a store listing needs, held to the limits the release check applies later.

    The description is at least 80 words and at most 4,000 characters, there are exactly seven keywords and
    they differ, and there are one to three categories, each an Amazon browse path of at least two levels
    (``Books > Business & Money``). These are the release contract's own rules (see BOOKS_AND_KDP.md), so a
    listing that is built here cannot fail that check for its shape. Every text is held to what a person can
    read: no control characters, and none that render as nothing or reorder what is shown.
    """

    MIN_DESCRIPTION_WORDS: ClassVar[int] = 80
    MAX_DESCRIPTION_CHARS: ClassVar[int] = 4_000
    MAX_TITLE_CHARS: ClassVar[int] = 120
    MAX_SUBTITLE_CHARS: ClassVar[int] = 200
    KEYWORDS: ClassVar[int] = 7
    MAX_KEYWORD_CHARS: ClassVar[int] = 50
    MAX_CATEGORIES: ClassVar[int] = 3
    MAX_CATEGORY_CHARS: ClassVar[int] = 200
    HIDDEN: ClassVar[frozenset[str]] = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"})

    title: str
    subtitle: str
    description: str
    keywords: tuple[str, ...]
    categories: tuple[str, ...]

    def __post_init__(self) -> None:
        self._line("the title", self.title, self.MAX_TITLE_CHARS)
        self._line("the subtitle", self.subtitle, self.MAX_SUBTITLE_CHARS)
        self._description()
        for label, values in (("keywords", self.keywords), ("categories", self.categories)):
            if not isinstance(values, tuple):
                raise TypeError(f"the {label} are a tuple")
        if len(self.keywords) != self.KEYWORDS:
            raise ValueError(
                f"a listing has exactly {self.KEYWORDS} keywords, not {len(self.keywords)}"
            )
        for keyword in self.keywords:
            self._line("a keyword", keyword, self.MAX_KEYWORD_CHARS)
        self._distinct("keywords", self.keywords)
        if not 1 <= len(self.categories) <= self.MAX_CATEGORIES:
            raise ValueError(
                f"a listing has one to {self.MAX_CATEGORIES} categories, not {len(self.categories)}"
            )
        for category in self.categories:
            self._category(category)
        self._distinct("categories", self.categories)

    def _description(self) -> None:
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("the description is empty")
        self._visible("the description", self.description.replace("\n", ""))
        if len(self.description) > self.MAX_DESCRIPTION_CHARS:
            raise ValueError(
                f"the description has {len(self.description)} characters; at most "
                f"{self.MAX_DESCRIPTION_CHARS} are allowed"
            )
        words = len(self.description.split())
        if words < self.MIN_DESCRIPTION_WORDS:
            raise ValueError(
                f"the description has {words} words; a listing needs at least {self.MIN_DESCRIPTION_WORDS}"
            )

    def _category(self, category: str) -> None:
        self._line("a category", category, self.MAX_CATEGORY_CHARS)
        levels = [level.strip() for level in category.split(">")]
        if len(levels) < 2 or any(not level for level in levels):
            raise ValueError(
                f"the category {category!r} is not a browse path of at least two levels "
                "such as 'Books > Business & Money'"
            )

    def _line(self, label: str, value: str, limit: int) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is empty")
        if len(value) > limit:
            raise ValueError(f"{label} is longer than {limit} characters")
        if value != value.strip() or "\n" in value:
            raise ValueError(f"{label} is one line with nothing before or after it")
        self._visible(label, value)

    def _visible(self, label: str, value: str) -> None:
        if any(unicodedata.category(character) in self.HIDDEN for character in value):
            raise ValueError(f"{label} has a control or invisible character in it")

    @staticmethod
    def _distinct(label: str, values: tuple[str, ...]) -> None:
        if len({value.casefold() for value in values}) != len(values):
            raise ValueError(f"the {label} must all differ")
