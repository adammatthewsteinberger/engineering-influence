# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FactClaimParser."""

from __future__ import annotations

from abc import ABC, abstractmethod


class FactClaimParserInterface(ABC):
    """Reads the fact checker's JSON answers, strictly: anything it cannot read is None, never a guess."""

    __slots__ = ()

    @abstractmethod
    def claims(self, text: str) -> tuple[tuple[str, str], ...] | None:
        """The claims a chapter was found to make, each with a search query, or None when the answer is unreadable."""

    @abstractmethod
    def verdict(self, text: str) -> tuple[bool, str] | None:
        """Whether a page supports a claim, and the quotation it gave, or None when the answer is unreadable."""
