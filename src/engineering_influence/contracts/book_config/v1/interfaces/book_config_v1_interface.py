# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BookConfigV1."""

from abc import ABC


class BookConfigV1Interface(ABC):
    """Version 1 of a book's config: what ``BookLoader`` reads from ``books/<slug>.toml``."""

    __slots__ = ()
