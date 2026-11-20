# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PdfDocument."""

from abc import ABC


class PdfDocumentInterface(ABC):
    """Every page of a PDF, and whether it carries bookmarks."""

    __slots__ = ()
