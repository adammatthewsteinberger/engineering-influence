"""One rendered page."""

from dataclasses import dataclass


@dataclass
class PageRecord:
    """Where a page image is, how big it is, and whether it is visually blank."""

    page: int
    path: str
    width: int
    height: int
    bytes: int
    blank: bool
