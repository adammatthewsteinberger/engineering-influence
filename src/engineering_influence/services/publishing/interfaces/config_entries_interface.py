# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ConfigEntries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class ConfigEntriesInterface(ABC):
    """Flattens front matter, parts and chapters, and back matter."""

    __slots__ = ()

    @abstractmethod
    def iterate(self, config: dict[str, Any]) -> list[tuple[str, str, str, int | None]]:
        """Return (kind, file, style, number) in printed order."""
