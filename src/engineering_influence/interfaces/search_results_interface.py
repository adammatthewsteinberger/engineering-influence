# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for the checks and the shaping that every search provider shares."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engineering_influence.errors.application_error import ApplicationError
    from engineering_influence.models.search_hit import SearchHit


class SearchResultsInterface(ABC):
    """Checks a query, shapes the result links, and makes the shared error."""

    __slots__ = ()

    @staticmethod
    @abstractmethod
    def check_query(query: str, count: int, max_characters: int, max_count: int) -> str:
        """The query with its whitespace tidied, or a SEARCH_QUERY_INVALID error."""

    @staticmethod
    @abstractmethod
    def hits(entries: list[Any], count: int) -> tuple[SearchHit, ...]:
        """The distinct links among the entries, best first, cut to `count`."""

    @staticmethod
    @abstractmethod
    def hit(entry: Any) -> SearchHit | None:
        """One result as a link and a title, or None when it is not a usable link."""

    @staticmethod
    @abstractmethod
    def error(code: str, message: str) -> ApplicationError:
        """A search failure the caller cannot fix by retrying: HTTP 502."""
