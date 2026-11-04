"""One chapter, front-matter, or back-matter file."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chapter:
    """A manuscript file with its parsed title, body, and optional epigraph."""

    path: Path
    kind: str  # "front", "chapter", "back"
    style: str = "prose"
    title: str = ""
    short: str = ""
    body: str = ""
    epigraph: tuple[str, str] | None = None
    number: int | None = None
