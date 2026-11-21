# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ForbiddenContentCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.text_policy import TextPolicy


class ForbiddenContentCheckInterface(ABC):
    """Dashes, placeholder markers, the word Draft, and the Edition line."""

    __slots__ = ()

    @abstractmethod
    def run(self, texts: list[str], edition: str, policy: TextPolicy) -> list[str]:
        """Return a problem for each forbidden item found in the page texts."""
