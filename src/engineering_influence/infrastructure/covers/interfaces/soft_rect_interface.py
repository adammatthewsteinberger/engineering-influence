# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SoftRect."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from numpy.typing import NDArray


class SoftRectInterface(ABC):
    """A rectangle of ones, blurred at the edges."""

    __slots__ = ()

    @abstractmethod
    def mask(self, h: int, w: int, box: tuple[int, int, int, int], feather: float) -> NDArray[Any]:
        """The feathered mask for a pixel box."""
