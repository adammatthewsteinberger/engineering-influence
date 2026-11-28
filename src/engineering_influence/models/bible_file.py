# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A card's file as the bible folder holds it: the folder is its kind, the file name is its id."""

import re
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.bible_file_interface import BibleFileInterface


@dataclass(frozen=True, slots=True)
class BibleFile(BibleFileInterface):
    """`kind` and `id` must be the folder and file-name forms ADR 0018 allows; `text` is the file as written."""

    KIND: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]*")
    ID: ClassVar[re.Pattern[str]] = re.compile(r"[a-z0-9][a-z0-9_-]*")

    kind: str
    id: str
    text: str

    def __post_init__(self) -> None:
        """Refuse a kind or id that the bible's folder and file-name rules do not allow."""
        if self.KIND.fullmatch(self.kind) is None:
            raise ValueError(f"a bible kind is a lowercase identifier, not {self.kind!r}")
        if self.ID.fullmatch(self.id) is None:
            raise ValueError(f"a bible id is a lowercase identifier, not {self.id!r}")

    def path(self) -> str:
        """The card's place in the bible, `kind/id.md`."""
        return f"{self.kind}/{self.id}.md"
