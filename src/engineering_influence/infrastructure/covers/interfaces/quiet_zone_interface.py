# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for QuietZone."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from numpy.typing import NDArray

    from engineering_influence.models.covers.cover_layout import CoverLayout


class QuietZoneInterface(ABC):
    """A soft mask over the back-cover text column and the spine."""

    __slots__ = ()

    @abstractmethod
    def mask(self, layout: CoverLayout, h: int, w: int) -> NDArray[Any]:
        """The mask for a layout and image size."""
