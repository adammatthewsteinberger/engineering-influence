# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Upload inspector port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.contracts.security_verdict import SecurityVerdict


class UploadInspectorInterface(ABC):
    """Judge an untrusted upload before anything reads it."""

    __slots__ = ()

    @abstractmethod
    def inspect(self, filename: str, content_type: str | None, content: bytes) -> SecurityVerdict:
        """Return the verdict for one upload."""
