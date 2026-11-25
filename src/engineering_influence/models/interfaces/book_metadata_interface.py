# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BookMetadata."""

from abc import ABC


class BookMetadataInterface(ABC):
    """The listing of a book: its title, subtitle, description, seven keywords and up to three categories."""

    __slots__ = ()
