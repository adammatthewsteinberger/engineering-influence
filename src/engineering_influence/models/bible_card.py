# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A bible card once its front matter is read: what it is, what it says about itself, and what it links to."""

import json
import re
from dataclasses import dataclass
from typing import Any, ClassVar

from engineering_influence.models.interfaces.bible_card_interface import BibleCardInterface


@dataclass(frozen=True, slots=True)
class BibleCard(BibleCardInterface):
    """`fields` is the TOML front matter as read; `body` is the Markdown after it, trimmed. A run keeps a card as JSON."""

    KIND: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]*")
    ID: ClassVar[re.Pattern[str]] = re.compile(r"[a-z0-9][a-z0-9_-]*")
    LINK: ClassVar[re.Pattern[str]] = re.compile(
        r"\[\[([a-z][a-z0-9_]*):\s*([a-z0-9][a-z0-9_-]*)\]\]"
    )

    kind: str
    id: str
    fields: dict[str, Any]
    body: str

    def __post_init__(self) -> None:
        if self.KIND.fullmatch(self.kind) is None:
            raise ValueError(f"a bible kind is a lowercase identifier, not {self.kind!r}")
        if self.ID.fullmatch(self.id) is None:
            raise ValueError(f"a bible id is a lowercase identifier, not {self.id!r}")

    def links(self) -> tuple[tuple[str, str], ...]:
        """Each `[[kind: id]]` in the body, as a (kind, id) pair, in the order written."""
        return tuple((match.group(1), match.group(2)) for match in self.LINK.finditer(self.body))

    def artifact(self) -> str:
        """The stored card's artifact name, `bible/kind/id.json`."""
        return f"bible/{self.kind}/{self.id}.json"

    def encode(self) -> str:
        """The card as JSON, so a run stores it and reads it back unchanged. A TOML date becomes its text."""
        return json.dumps(
            {"kind": self.kind, "id": self.id, "fields": self.fields, "body": self.body},
            default=str,
            sort_keys=True,
        )

    @classmethod
    def decode(cls, text: str) -> "BibleCard":
        """The card a run stored with `encode`."""
        data = json.loads(text)
        return cls(data["kind"], data["id"], data["fields"], data["body"])
