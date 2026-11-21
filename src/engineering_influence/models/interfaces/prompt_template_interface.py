# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PromptTemplate."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


class PromptTemplateInterface(ABC):
    """A versioned prompt, written once, with its blanks and the text that must be treated as data."""

    __slots__ = ()

    @abstractmethod
    def identifier(self) -> str:
        """The name and version, as recorded in the run journal: ``chapter_draft@3``."""

    @abstractmethod
    def render(self, part: str, values: Mapping[str, str] | None = None) -> str:
        """The part with every blank filled; the blanks and the values must match exactly."""

    @abstractmethod
    def fingerprint(self) -> str:
        """A hash of everything that changes what the model sees; the description is left out."""
