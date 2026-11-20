# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BlankPageDetector."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


class BlankPageDetectorInterface(ABC):
    """A page is blank when nothing on it is darker than light gray."""

    __slots__ = ()

    @abstractmethod
    def is_blank(self, image: Image.Image) -> bool:
        """True for a white page; a nearly white page with a tiny mark is not blank."""
