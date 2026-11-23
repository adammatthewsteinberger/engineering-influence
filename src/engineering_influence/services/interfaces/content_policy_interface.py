# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ContentPolicy."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_brief import BookBrief
    from engineering_influence.models.provider_descriptor import ProviderDescriptor


class ContentPolicyInterface(ABC):
    """Says whether a model is recorded as allowing the violence and heat a brief asks for."""

    __slots__ = ()

    @abstractmethod
    def problems(self, brief: BookBrief, model: ProviderDescriptor) -> tuple[str, ...]:
        """One sentence for each level the brief asks for that the model is not recorded as allowing."""

    @abstractmethod
    def require(self, brief: BookBrief, model: ProviderDescriptor) -> None:
        """Return when the model allows the brief, or raise an ApplicationError (CONTENT_LEVEL_NOT_ALLOWED) saying why not."""
