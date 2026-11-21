# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for TextPolicy."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.text_policy import TextPolicy


class TextPolicyInterface(ABC):
    """The house rules for printed text, which differ between a novel and a non-fiction book."""

    __slots__ = ()

    @classmethod
    @abstractmethod
    def for_name(cls, name: str | None) -> TextPolicy:
        """The policy for a config's ``kind`` setting; a book that sets none is non-fiction."""
