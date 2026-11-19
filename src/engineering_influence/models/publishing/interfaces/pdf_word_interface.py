# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A word on a PDF page."""

from abc import ABC


class PdfWordInterface(ABC):
    """Marker for the PdfWord value object; it declares no behaviour."""

    __slots__ = ()
