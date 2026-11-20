# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Version 1 of the brief: the one document that starts a book run."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from engineering_influence.contracts.brief.v1.interfaces.book_brief_v1_interface import (
    BookBriefV1Interface,
)
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class BookBriefV1(BookBriefV1Interface, BaseModel):
    """What the person asking for a book supplies; unknown fields are refused.

    Version 1 carries the idea, the kind of book and a required spending cap in whole
    micro-dollars. Later compatible versions may add optional fields; they will not change
    these.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = 1
    kind: BookKind
    idea: NonBlank
    budget_micro_usd: int = Field(gt=0)
    title_hint: NonBlank | None = None
    audience: NonBlank | None = None
    target_words: int | None = Field(default=None, gt=0)
    trim_size: NonBlank | None = None
    language: NonBlank = "en"

    def to_model(self) -> BookBrief:
        """The same brief as the pure model a run is built from."""
        return BookBrief(
            kind=self.kind,
            idea=self.idea,
            budget_micro_usd=self.budget_micro_usd,
            title_hint=self.title_hint,
            audience=self.audience,
            target_words=self.target_words,
            trim_size=self.trim_size,
            language=self.language,
        )
