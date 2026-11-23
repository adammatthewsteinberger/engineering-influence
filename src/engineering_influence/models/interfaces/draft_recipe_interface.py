# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for DraftRecipe."""

from abc import ABC, abstractmethod
from collections.abc import Mapping


class DraftRecipeInterface(ABC):
    """What a kind of book reads to draft a chapter, how it labels it, and what it tells the model to do."""

    __slots__ = ()

    @abstractmethod
    def style_text(self, texts: Mapping[str, str]) -> str:
        """The voice part of the context: each labelled input, in order."""

    @abstractmethod
    def grounding_text(self, texts: Mapping[str, str]) -> str:
        """The part of the context the chapter is grounded in: each labelled input, in order."""

    @abstractmethod
    def instruction_text(
        self, number: int, count: int, words: int, violence: str, heat: str
    ) -> str:
        """The one plain-text instruction for a chapter, from numbers and two closed-set levels."""
