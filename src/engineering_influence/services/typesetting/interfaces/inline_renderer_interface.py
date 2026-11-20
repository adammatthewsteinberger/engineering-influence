# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for InlineRenderer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdown_it.token import Token


class InlineRendererInterface(ABC):
    """Renders emphasis, code, links, and bare URLs."""

    __slots__ = ()

    @abstractmethod
    def text(self, s: str) -> str:
        """Escape text; bare URLs become breakable \\url{}."""

    @abstractmethod
    def inline(self, tokens: list[Token]) -> str:
        """Render a paragraph's inline tokens."""
