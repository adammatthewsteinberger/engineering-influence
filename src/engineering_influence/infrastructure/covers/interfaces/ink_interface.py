# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Ink."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from numpy.typing import NDArray


class InkInterface(ABC):
    """Draws at `scale` times the resolution, then reduces to a float mask in [0, 1]."""

    __slots__ = ()

    @abstractmethod
    def line(self, pts: Any, width_px: float, value: int = 255) -> None:
        """A curved-joint polyline."""

    @abstractmethod
    def ellipse(
        self,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        value: int = 255,
        outline_px: float | None = None,
    ) -> None:
        """A filled or outlined ellipse."""

    @abstractmethod
    def polygon(self, pts: Any, value: int = 255) -> None:
        """A filled polygon."""

    @abstractmethod
    def mask(self) -> NDArray[Any]:
        """The accumulated coverage as float32 in [0, 1]."""
