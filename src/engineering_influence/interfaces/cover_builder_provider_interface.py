# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for obtaining a cover builder when one is needed."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.interfaces.cover_builder_interface import CoverBuilderInterface


class CoverBuilderProviderInterface(ABC):
    """Supply a cover builder, set up on demand rather than when the project is loaded."""

    __slots__ = ()

    @abstractmethod
    def provide(self) -> CoverBuilderInterface:
        """Load the cover plugins and return a builder that uses them."""
