# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One configured manuscript entry."""

from dataclasses import dataclass

from engineering_influence.models.publishing.interfaces.entry_interface import EntryInterface


@dataclass
class Entry(EntryInterface):
    """A front-matter, chapter, or back-matter file as printed."""

    kind: str
    file: str
    title: str = ""
    style: str = "prose"
    number: int | None = None
    words: int = 0
    first_paragraph: str = ""
