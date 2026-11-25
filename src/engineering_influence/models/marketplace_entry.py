# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One plugin a Claude Code marketplace lists: a name, where it says the plugin lives, and nothing fetched."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.marketplace_entry_interface import (
    MarketplaceEntryInterface,
)


@dataclass(frozen=True, slots=True)
class MarketplaceEntry(MarketplaceEntryInterface):
    """A name, a one-line description, a version if it gave one, and its source as ``kind`` and ``target``.

    The source is **text to read**, never an address that is contacted: ``path`` is a folder inside the marketplace,
    ``github`` a repository, ``url`` a git address, and ``other`` anything else. ``local`` is the folder on this
    machine a ``path`` source points to when the marketplace itself is a local folder, and empty otherwise.
    """

    KINDS: ClassVar[frozenset[str]] = frozenset({"path", "github", "url", "other"})
    MAX_NAME_CHARS: ClassVar[int] = 100
    MAX_DESCRIPTION_CHARS: ClassVar[int] = 300
    MAX_TARGET_CHARS: ClassVar[int] = 300

    name: str
    description: str
    kind: str
    target: str
    version: str = ""
    local: str = ""

    def __post_init__(self) -> None:
        for label, value, limit in (
            ("name", self.name, self.MAX_NAME_CHARS),
            ("description", self.description, self.MAX_DESCRIPTION_CHARS),
            ("target", self.target, self.MAX_TARGET_CHARS),
            ("version", self.version, 50),
            ("local", self.local, 1_000),
        ):
            if not isinstance(value, str) or len(value) > limit or not value.isprintable():
                raise ValueError(
                    f"a listed plugin's {label} is one line of printable text, at most {limit} characters"
                )
        if not self.name:
            raise ValueError("a listed plugin has a name")
        if self.kind not in self.KINDS:
            raise ValueError(f"a source is one of {sorted(self.KINDS)}")
        if self.local and self.kind != "path":
            raise ValueError("only a path source has a local folder")

    def identifier(self) -> str:
        """The name, with ``@version`` when it gave one."""
        return f"{self.name}@{self.version}" if self.version else self.name
