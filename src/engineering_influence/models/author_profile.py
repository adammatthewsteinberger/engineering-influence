# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The author's own details for a book's title page, copyright page and about-the-author page."""

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, ClassVar

from engineering_influence.models.book_pricing import BookPricing
from engineering_influence.models.interfaces.author_profile_interface import AuthorProfileInterface


@dataclass(frozen=True, slots=True)
class AuthorProfile(AuthorProfileInterface):
    """What only the author can say: who they are, who publishes the book, which edition and year.

    The author, the publisher, the edition and the bio are required, because the typesetter will not build a
    book without them. The edition has to say ``Edition`` (the text check looks for it). The rest are
    optional, and so is the pricing, which a strict release needs (see ``BookPricing``). A bio, a dedication and the copyright notes may run to several paragraphs; everything else is
    one line. Every text is held to what a person can read, with no control or invisible characters.

    These are the author's, so they are supplied to a run (see ``EI_AUTHOR_PROFILE`` in CONFIGURATION.md)
    and are never part of this repository.
    """

    ISBN: ClassVar[re.Pattern[str]] = re.compile(r"[0-9][0-9-]{8,20}[0-9Xx]")
    MAX_LINE_CHARS: ClassVar[int] = 200
    MAX_TEXT_CHARS: ClassVar[int] = 4_000
    MAX_ALSO_BY: ClassVar[int] = 20
    HIDDEN: ClassVar[frozenset[str]] = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"})

    author: str
    publisher: str
    edition: str
    author_bio: str
    year: int | None = None
    website: str = ""
    email: str = ""
    isbn: str = ""
    ebook_isbn: str = ""
    dedication: str = ""
    copyright_notes: str = ""
    also_by: tuple[str, ...] = ()
    pricing: BookPricing | None = None

    def __post_init__(self) -> None:
        """Validate the author's details when the profile is built."""
        for label, value in (
            ("author", self.author),
            ("publisher", self.publisher),
            ("edition", self.edition),
        ):
            self._line(label, value, required=True)
        if "Edition" not in self.edition:
            raise ValueError("the edition has to say 'Edition', as in 'First Edition'")
        self._text("author_bio", self.author_bio, required=True)
        for label, value in (
            ("dedication", self.dedication),
            ("copyright_notes", self.copyright_notes),
        ):
            self._text(label, value, required=False)
        if self.year is not None and (type(self.year) is not int or not 1000 <= self.year <= 9999):
            raise ValueError("the year is a four digit number")
        for label, value in (("website", self.website), ("email", self.email)):
            self._line(label, value, required=False)
        if self.email and ("@" not in self.email or " " in self.email):
            raise ValueError("the email is not an address")
        for label, value in (("isbn", self.isbn), ("ebook_isbn", self.ebook_isbn)):
            self._line(label, value, required=False)
            if value and not self.ISBN.fullmatch(value):
                raise ValueError(f"{label} is digits and hyphens, ending in a digit or X")
        if not isinstance(self.also_by, tuple) or len(self.also_by) > self.MAX_ALSO_BY:
            raise ValueError(f"also_by is a tuple of at most {self.MAX_ALSO_BY} titles")
        for title in self.also_by:
            self._line("an also_by title", title, required=True)
        if self.pricing is not None and not isinstance(self.pricing, BookPricing):
            raise TypeError("pricing is a BookPricing")

    def entries(self) -> dict[str, Any]:
        """The book config entries this profile sets, in the order they are written; empty ones are left out."""
        candidates: tuple[tuple[str, Any], ...] = (
            ("author", self.author),
            ("publisher", self.publisher),
            ("edition", self.edition),
            ("year", self.year),
            ("author_bio", self.author_bio),
            ("website", self.website),
            ("email", self.email),
            ("isbn", self.isbn),
            ("ebook_isbn", self.ebook_isbn),
            ("dedication", self.dedication),
            ("copyright_notes", self.copyright_notes),
            ("also_by", list(self.also_by)),
        )
        return {key: value for key, value in candidates if value not in ("", None, [])}

    def _line(self, label: str, value: str, *, required: bool) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{label} is text")
        if not value:
            if required:
                raise ValueError(f"{label} is required")
            return
        if not value.strip() or value != value.strip() or "\n" in value:
            raise ValueError(f"{label} is one line with nothing before or after it")
        if len(value) > self.MAX_LINE_CHARS:
            raise ValueError(f"{label} is longer than {self.MAX_LINE_CHARS} characters")
        self._visible(label, value)

    def _text(self, label: str, value: str, *, required: bool) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{label} is text")
        if not value.strip():
            if required or value:
                raise ValueError(f"{label} is required" if required else f"{label} is blank")
            return
        if len(value) > self.MAX_TEXT_CHARS:
            raise ValueError(f"{label} is longer than {self.MAX_TEXT_CHARS} characters")
        self._visible(label, value.replace("\n", "").replace("\t", ""))

    def _visible(self, label: str, value: str) -> None:
        if any(unicodedata.category(character) in self.HIDDEN for character in value):
            raise ValueError(f"{label} has a control or invisible character in it")
