# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ApiApplication."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class ApiApplicationInterface(ABC):
    """Builds the REST application without duplicating application logic."""

    __slots__ = ()

    @abstractmethod
    def build(self) -> Any:
        """Return a FastAPI app with the public project-start contract."""
