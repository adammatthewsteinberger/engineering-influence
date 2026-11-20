# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A source a non-fiction book leans on, pinned by the hash of what was fetched."""

from dataclasses import dataclass, replace

from engineering_influence.models.interfaces.source_record_interface import (
    SourceRecordInterface,
)


@dataclass(frozen=True, slots=True)
class SourceRecord(SourceRecordInterface):
    """Where a claim came from and whether the fetched text was checked against it."""

    url: str
    title: str
    content_hash: str
    verified: bool = False

    def __post_init__(self) -> None:
        if not self.url.strip() or not self.content_hash.strip():
            raise ValueError("a source needs a url and a content hash")

    def mark_verified(self) -> "SourceRecord":
        """The same source once its text has been checked against the claim."""
        return replace(self, verified=True)
