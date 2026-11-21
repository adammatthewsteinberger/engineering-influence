# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: turning what a server sent into the text a reader would see."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.page_text import PageText


class PageTextExtractorInterface(ABC):
    """Reads HTML or plain text, and keeps only what a reader would see."""

    __slots__ = ()

    @abstractmethod
    def extract_html(self, content: str) -> PageText:
        """The title and visible text of an HTML page."""

    @abstractmethod
    def extract_plain(self, content: str) -> PageText:
        """The text of a plain-text page, cleaned the same way."""
