# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: where the product's prompt templates come from."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.prompt_template import PromptTemplate


class PromptLibraryInterface(ABC):
    """The prompts the product sends to a model, by name."""

    __slots__ = ()

    @abstractmethod
    def names(self) -> list[str]:
        """Every template name, sorted."""

    @abstractmethod
    def get(self, name: str) -> PromptTemplate:
        """The named template, or an ApplicationError (PROMPT_TEMPLATE_INVALID) when it is not valid."""
