# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PdfPage."""

from abc import ABC


class PdfPageInterface(ABC):
    """One page: sizes, text, words, the box its text fills, and structural flags."""

    __slots__ = ()
