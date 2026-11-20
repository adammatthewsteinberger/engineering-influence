# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A book assembled from its configuration and manuscript files."""

from dataclasses import dataclass, field
from typing import Any

from engineering_influence.models.typesetting.chapter import Chapter
from engineering_influence.models.typesetting.interfaces.book_interface import BookInterface


@dataclass
class Book(BookInterface):
    """Metadata plus front matter, parts of chapters, and back matter."""

    slug: str
    meta: dict[str, Any]
    front: list[Chapter] = field(default_factory=list)
    parts: list[tuple[str, list[Chapter]]] = field(default_factory=list)
    back: list[Chapter] = field(default_factory=list)
