# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BlockRenderer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdown_it.token import Token


class BlockRendererInterface(ABC):
    """Renders headings, paragraphs, lists, quotes, tables, and code."""

    __slots__ = ()

    @abstractmethod
    def render(self, tokens: list[Token]) -> str:
        """Render a token stream."""
