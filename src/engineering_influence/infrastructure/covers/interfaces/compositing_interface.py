# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Compositing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from numpy.typing import NDArray


class CompositingInterface(ABC):
    """Smoothstep, mixing, colours, and in-place compositing through masks."""

    __slots__ = ()

    @abstractmethod
    def smoothstep(self, e0: float, e1: float, x: NDArray[Any]) -> NDArray[Any]:
        """Hermite interpolation between two edges."""

    @abstractmethod
    def mix(self, a: Any, b: Any, t: Any) -> Any:
        """Linear blend from a to b."""

    @abstractmethod
    def rgb(self, *c: float) -> NDArray[Any]:
        """A float32 colour."""

    @abstractmethod
    def over(self, img: NDArray[Any], mask: NDArray[Any], color: Any, alpha: float = 1.0) -> None:
        """Composite a flat colour through a coverage mask, in place."""

    @abstractmethod
    def add_light(
        self, img: NDArray[Any], mask: NDArray[Any], color: Any, gain: float = 1.0
    ) -> None:
        """Additive light (glows), in place."""
