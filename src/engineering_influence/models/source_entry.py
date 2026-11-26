# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A source file as a run stores it: numbered, named as an artifact, and pinned by a SHA-256 digest."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.source_entry_interface import SourceEntryInterface


@dataclass(frozen=True, slots=True)
class SourceEntry(SourceEntryInterface):
    """`number` orders the sources (1 is first); `digest` is the hex SHA-256 of the text, so a changed source is seen."""

    number: int
    text: str
    digest: str

    def __post_init__(self) -> None:
        if type(self.number) is not int or self.number < 1:
            raise ValueError("a source entry is numbered from 1")
        if len(self.digest) != 64:
            raise ValueError("a source entry's digest is a 64-character SHA-256 hex string")

    def artifact(self) -> str:
        """The artifact name, `source/NNN.md`."""
        return f"source/{self.number:03d}.md"
