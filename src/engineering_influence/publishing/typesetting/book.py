# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A book assembled from its configuration and manuscript files."""

from dataclasses import dataclass, field
from typing import Any

from engineering_influence.publishing.typesetting.chapter import Chapter


@dataclass
class Book:
    """Metadata plus front matter, parts of chapters, and back matter."""

    slug: str
    meta: dict[str, Any]
    front: list[Chapter] = field(default_factory=list)
    parts: list[tuple[str, list[Chapter]]] = field(default_factory=list)
    back: list[Chapter] = field(default_factory=list)
