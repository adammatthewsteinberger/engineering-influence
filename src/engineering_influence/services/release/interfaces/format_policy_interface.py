# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FormatPolicy."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class FormatPolicyInterface(ABC):
    """Keeps old books compatible: no [formats] table means no hardcover."""

    __slots__ = ()

    @abstractmethod
    def of(self, config: dict[str, Any]) -> dict[str, Any]:
        """The explicit format policy."""
