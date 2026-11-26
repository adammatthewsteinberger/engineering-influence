# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Version 1 of the brief: the one document that starts a book run."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from engineering_influence.contracts.brief.v1.interfaces.book_brief_v1_interface import (
    BookBriefV1Interface,
)
from engineering_influence.contracts.brief.v1.run_input_v1 import RunInputV1
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.run_input import RunInput

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class BookBriefV1(BookBriefV1Interface, BaseModel):
    """What the person asking for a book supplies; unknown fields are refused.

    Version 1 carries the idea, the kind of book and a required spending cap in whole
    micro-dollars. Later compatible versions may add optional fields; they will not change
    these. ``inputs`` is such a field: text the person gave the run, none by default, so every
    brief written before it still reads the same. So are ``violence`` and ``heat``, the levels a novel may go to.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = 1
    kind: BookKind
    idea: NonBlank
    budget_micro_usd: int = Field(gt=0)
    title_hint: NonBlank | None = None
    audience: NonBlank | None = None
    target_words: int | None = Field(default=None, gt=0)
    trim_size: Literal["5x8", "5.5x8.5", "6x9"] | None = None
    language: NonBlank = "en"
    inputs: list[RunInputV1] = Field(default_factory=list, max_length=BookBrief.MAX_INPUTS)
    violence: Literal["none", "mild", "moderate", "graphic"] | None = None
    heat: Literal["none", "sweet", "steamy", "explicit"] | None = None

    @model_validator(mode="after")
    def _check(self) -> "BookBriefV1":
        if self.kind is BookKind.SCREENPLAY:
            raise ValueError(
                "screenplay runs are not yet available; the screenplay plan lands in later pull requests"
            )
        self.to_model()
        return self

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
            inputs=tuple(RunInput(item.name, item.text, item.origin) for item in self.inputs),
            violence=self.violence,
            heat=self.heat,
        )
