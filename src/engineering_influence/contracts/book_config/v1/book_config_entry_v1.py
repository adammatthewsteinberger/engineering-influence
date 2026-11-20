# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Version 1 of one file listed in a book's config."""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from engineering_influence.contracts.book_config.v1.interfaces.book_config_entry_v1_interface import (
    BookConfigEntryV1Interface,
)

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class BookConfigEntryV1(BookConfigEntryV1Interface, BaseModel):
    """A manuscript file, written either as a bare name or as a table with a style."""

    model_config = ConfigDict(frozen=True)

    file: NonBlank
    style: NonBlank = "prose"
    short: NonBlank | None = None

    @model_validator(mode="before")
    @classmethod
    def _accept_a_bare_name(cls, value: Any) -> Any:
        return {"file": value} if isinstance(value, str) else value
