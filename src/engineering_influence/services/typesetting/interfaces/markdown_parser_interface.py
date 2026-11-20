# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for MarkdownParser."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdown_it.token import Token


class MarkdownParserInterface(ABC):
    """CommonMark with smart quotes, tables, and strikethrough."""

    __slots__ = ()

    @abstractmethod
    def parse(self, text: str) -> list[Token]:
        """Parse block-level Markdown."""

    @abstractmethod
    def parse_inline(self, text: str) -> list[Token]:
        """Parse inline-only Markdown."""

    @abstractmethod
    def render_inline(self, text: str) -> str:
        """Render inline Markdown to HTML (used to match the pages' curly quotes)."""
