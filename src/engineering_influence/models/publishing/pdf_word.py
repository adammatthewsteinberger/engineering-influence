# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One word on a PDF page, with its vertical position."""

from dataclasses import dataclass

from engineering_influence.models.publishing.interfaces.pdf_word_interface import PdfWordInterface


@dataclass(frozen=True, slots=True)
class PdfWord(PdfWordInterface):
    """A word's text and where it sits between the top and the bottom of the page."""

    text: str
    top: float
    bottom: float
