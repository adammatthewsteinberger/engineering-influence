"""One configured manuscript entry."""

from dataclasses import dataclass


@dataclass
class Entry:
    """A front-matter, chapter, or back-matter file as printed."""

    kind: str
    file: str
    title: str = ""
    style: str = "prose"
    number: int | None = None
    words: int = 0
    first_paragraph: str = ""
