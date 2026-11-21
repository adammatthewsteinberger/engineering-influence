# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: reading one web page as evidence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.fetched_page import FetchedPage


class SourceFetcherInterface(ABC):
    """Fetches a page and returns the text a reader would see."""

    __slots__ = ()

    @abstractmethod
    def fetch(self, url: str) -> FetchedPage:
        """The page, or an ApplicationError (a SOURCE_* code) when it cannot be used.

        Raise ``TransientStageError`` when trying again could work: a timeout, a dropped
        connection, a 429 or a 5xx.
        """
