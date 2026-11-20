# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Version 1 of a book's config: what ``BookLoader`` reads from ``books/<slug>.toml``."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from engineering_influence.contracts.book_config.v1.book_config_entry_v1 import BookConfigEntryV1
from engineering_influence.contracts.book_config.v1.book_config_part_v1 import BookConfigPartV1
from engineering_influence.contracts.book_config.v1.interfaces.book_config_v1_interface import (
    BookConfigV1Interface,
)

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class BookConfigV1(BookConfigV1Interface, BaseModel):
    """The structural keys of a book config; every other key is kept as metadata.

    ``source`` names the manuscript directory. ``front``, ``parts`` and ``back`` give the
    printed order, and ``not_in_book`` lists Markdown files the loader should not insist on.
    Title, author, release and format tables are free-form for now and travel as extras.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    source: NonBlank
    front: tuple[BookConfigEntryV1, ...] = ()
    parts: tuple[BookConfigPartV1, ...] = ()
    back: tuple[BookConfigEntryV1, ...] = ()
    not_in_book: tuple[NonBlank, ...] = ()
