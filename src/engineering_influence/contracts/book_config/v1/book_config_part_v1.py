# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Version 1 of one part of a book: a title and the chapters under it."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from engineering_influence.contracts.book_config.v1.book_config_entry_v1 import BookConfigEntryV1
from engineering_influence.contracts.book_config.v1.interfaces.book_config_part_v1_interface import (
    BookConfigPartV1Interface,
)

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class BookConfigPartV1(BookConfigPartV1Interface, BaseModel):
    """A part's title and its chapter files, in reading order."""

    model_config = ConfigDict(frozen=True)

    title: NonBlank
    chapters: tuple[BookConfigEntryV1, ...]
