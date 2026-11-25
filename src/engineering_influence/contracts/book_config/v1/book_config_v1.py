# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Version 1 of a book's config: what ``BookLoader`` reads from ``books/<slug>.toml``."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from engineering_influence.contracts.book_config.v1.book_config_entry_v1 import BookConfigEntryV1
from engineering_influence.contracts.book_config.v1.book_config_part_v1 import BookConfigPartV1
from engineering_influence.contracts.book_config.v1.interfaces.book_config_v1_interface import (
    BookConfigV1Interface,
)
from engineering_influence.models.book_kind import BookKind

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class BookConfigV1(BookConfigV1Interface, BaseModel):
    """The structural keys of a book config; every other key is kept as metadata.

    ``kind`` is ``nonfiction`` unless the config says ``novel``; it picks the text policy.
    ``trim_size`` and ``paper`` default to 6x9 and white and decide the page size and spine width.
    ``source`` names the manuscript directory. ``front``, ``parts`` and ``back`` give the
    printed order, and ``not_in_book`` lists Markdown files the loader should not insist on.
    Title, author, release and format tables are free-form for now and travel as extras. ``schema_version`` is 1; a config
    that does not say is read as version 1, so every book written before it existed still loads.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    schema_version: Literal[1] = 1
    source: NonBlank
    kind: BookKind = BookKind.NONFICTION
    trim_size: Literal["5x8", "5.5x8.5", "6x9"] = "6x9"
    paper: Literal["white", "cream"] = "white"
    front: tuple[BookConfigEntryV1, ...] = ()
    parts: tuple[BookConfigPartV1, ...] = ()
    back: tuple[BookConfigEntryV1, ...] = ()
    not_in_book: tuple[NonBlank, ...] = ()
