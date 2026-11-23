# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for AuthorProfile."""

from abc import ABC, abstractmethod
from typing import Any


class AuthorProfileInterface(ABC):
    """The author's own details for a book's title page, copyright page and about-the-author page."""

    __slots__ = ()

    @abstractmethod
    def entries(self) -> dict[str, Any]:
        """The book config entries this profile sets, in the order they are written; empty ones are left out."""
