# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FilmGrain."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    import numpy as np
    from numpy.typing import NDArray


class FilmGrainInterface(ABC):
    """Adds zero-mean noise to an image in place."""

    __slots__ = ()

    @abstractmethod
    def add(self, img: NDArray[Any], rng: np.random.Generator, amount: float) -> None:
        """Add grain of the given amplitude."""
