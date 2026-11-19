# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The facts the checks need about one page of a finished interior."""

from dataclasses import dataclass

from engineering_influence.models.publishing.interfaces.pdf_page_interface import PdfPageInterface
from engineering_influence.models.publishing.pdf_word import PdfWord


@dataclass(frozen=True, slots=True)
class PdfPage(PdfPageInterface):
    """One page: sizes, text, words, the box its text fills, and structural flags.

    ``width`` and ``height`` are the page size the text extractor reports; ``media_width`` and
    ``media_height`` are the MediaBox. ``text_box`` is (x0, x1, top, bottom) over every
    character, or None for a blank page.
    """

    width: float
    height: float
    media_width: float
    media_height: float
    text: str
    words: tuple[PdfWord, ...]
    text_box: tuple[float, float, float, float] | None
    has_annotations: bool
    has_group: bool
    unembedded_fonts: frozenset[str]
