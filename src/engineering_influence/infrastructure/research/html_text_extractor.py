# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Keeps what a reader of a page would see, and drops what is only there for a machine."""

import re
import unicodedata

from engineering_influence.infrastructure.research.html_collector import HtmlCollector
from engineering_influence.interfaces.page_text_extractor_interface import (
    PageTextExtractorInterface,
)
from engineering_influence.models.page_text import PageText


class HtmlTextExtractor(PageTextExtractorInterface):
    """Visible text only, so a page cannot hide instructions where a reader would not see them.

    Dropped: ``script``, ``style`` and other non-content elements, comments, anything marked
    ``hidden``, ``aria-hidden="true"`` or styled ``display:none`` or ``visibility:hidden`` (with
    everything inside it), and invisible format characters such as zero-width spaces and
    right-to-left overrides. Text that a reader can see stays, even when it reads like an
    instruction: that is data to be quoted as evidence, not something to censor here.

    Every call builds its own collector, so one extractor can be shared between threads.
    """

    def extract_html(self, content: str) -> PageText:
        """The title and visible text of an HTML page."""
        collector = HtmlCollector()
        collector.feed(content)
        collector.close()
        title, text = collector.collected()
        return PageText(self._line(title), self._clean(text))

    def extract_plain(self, content: str) -> PageText:
        """The text of a plain-text page, cleaned the same way."""
        return PageText("", self._clean(content))

    def _line(self, text: str) -> str:
        return " ".join(self._visible(text).split())

    def _clean(self, text: str) -> str:
        lines = [" ".join(line.split()) for line in self._visible(text).splitlines()]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()

    @staticmethod
    def _visible(text: str) -> str:
        return "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
