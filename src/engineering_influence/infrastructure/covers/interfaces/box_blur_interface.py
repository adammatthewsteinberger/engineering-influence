# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BoxBlur."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from numpy.typing import NDArray


class BoxBlurInterface(ABC):
    """Three separable box blurs, edge-clamped."""

    __slots__ = ()

    @abstractmethod
    def apply(self, a: NDArray[Any], sigma: float) -> NDArray[Any]:
        """Blur `a` by roughly `sigma` pixels; below 0.5 the input is returned unchanged."""
