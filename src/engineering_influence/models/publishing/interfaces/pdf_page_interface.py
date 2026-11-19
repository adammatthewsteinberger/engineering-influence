# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A page of a finished PDF."""

from abc import ABC


class PdfPageInterface(ABC):
    """Marker for the PdfPage value object; it declares no behaviour."""

    __slots__ = ()
