# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CassetteInteraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CassetteInteractionInterface(ABC):
    """One recorded request and the answer that came back."""

    __slots__ = ()

    @abstractmethod
    def mismatch(self, method: str, path: str, body: Any) -> str:
        """Why a request is not the recorded one, or an empty string when it is."""
