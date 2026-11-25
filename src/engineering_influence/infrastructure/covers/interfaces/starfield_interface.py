# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Starfield."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    import numpy as np
    from numpy.typing import NDArray


class StarfieldInterface(ABC):
    """Brightness follows a power law, with a slight colour-temperature spread."""

    __slots__ = ()

    @abstractmethod
    def add(
        self,
        img: NDArray[Any],
        rng: np.random.Generator,
        density_per_sq_in: float,
        ppi: float,
        weight: NDArray[Any] | None = None,
        max_gain: float = 1.0,
    ) -> None:
        """Add stars to `img` in place."""
