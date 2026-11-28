# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for AnswerScreen."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AnswerScreenInterface(ABC):
    """Tells a refusal from prose, and a section that is far too short from one that is not."""

    __slots__ = ()

    @abstractmethod
    def refused(self, text: str) -> bool:
        """Whether the answer opens by declining to write the text."""

    @abstractmethod
    def short(self, text: str, asked_words: int) -> bool:
        """Whether the answer is well under the length that was asked for."""
