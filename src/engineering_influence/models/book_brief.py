# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a person asks for: the seed of a book and the money they will spend on it."""

from dataclasses import dataclass

from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.interfaces.book_brief_interface import BookBriefInterface


@dataclass(frozen=True, slots=True)
class BookBrief(BookBriefInterface):
    """An idea, a kind of book and a spending cap; everything else has a default.

    ``budget_micro_usd`` is required so that no run can start without a cap. It is whole
    micro-dollars, the same unit as ``Budget``.
    """

    kind: BookKind
    idea: str
    budget_micro_usd: int
    title_hint: str | None = None
    audience: str | None = None
    target_words: int | None = None
    trim_size: str | None = None
    language: str = "en"

    def __post_init__(self) -> None:
        if not self.idea.strip():
            raise ValueError("a brief needs an idea")
        if self.budget_micro_usd <= 0:
            raise ValueError("a brief needs a positive budget")
        if self.target_words is not None and self.target_words <= 0:
            raise ValueError("target words must be positive")
        if not self.language.strip():
            raise ValueError("a brief needs a language")
        for text in (self.title_hint, self.audience, self.trim_size):
            if text is not None and not text.strip():
                raise ValueError("optional brief text cannot be blank")
