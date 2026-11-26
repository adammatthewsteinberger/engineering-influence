# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplayAnchorsCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplayAnchorsCheckInterface(ABC):
    """The mechanical checks on a screenplay's anchors (prompt 08, step 8.0)."""

    __slots__ = ()

    @abstractmethod
    def problems(self, text: str) -> tuple[str, ...]:
        """Every missing section and rule the anchors break, or nothing when they pass."""
