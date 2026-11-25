# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Model profile loader port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.model_profile import ModelProfile


class ModelProfileLoaderInterface(ABC):
    """Read a deployment's model profiles from wherever they are kept."""

    __slots__ = ()

    @abstractmethod
    def load(self, path: Path) -> tuple[ModelProfile, ...]:
        """Parse the profiles at ``path``; raise an ApplicationError that names what is wrong."""
