# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: finding web pages about a topic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.search_hit import SearchHit


class SearchProviderInterface(ABC):
    """Runs one web search."""

    __slots__ = ()

    @abstractmethod
    def search(self, query: str, count: int) -> tuple[SearchHit, ...]:
        """Up to ``count`` distinct links for the query, best first, or none.

        Raise ``TransientStageError`` for a failure worth retrying and ``CapacityExhaustedError``
        when the key or quota is gone. The query leaves this machine for the vendor.
        """
