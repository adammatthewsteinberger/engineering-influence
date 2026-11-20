# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for TextStatistics."""

from abc import ABC, abstractmethod


class TextStatisticsInterface(ABC):
    """Counts reader-visible words and source URLs."""

    __slots__ = ()

    @abstractmethod
    def words(self, text: str) -> int:
        """Count words in plain text."""

    @abstractmethod
    def urls(self, text: str) -> int:
        """Count http(s) URLs."""

    @abstractmethod
    def is_url(self, text: str) -> bool:
        """Return True when the whole text is one http(s) URL."""

    @abstractmethod
    def reader_words(self, markdown: str) -> int:
        """Count words without counting Markdown punctuation, code, or link targets."""
