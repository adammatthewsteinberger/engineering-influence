# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CoverPluginLoader."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.infrastructure.covers.painter_registry import PainterRegistry
    from engineering_influence.models.covers.cover_style import CoverStyle


class CoverPluginLoaderInterface(ABC):
    """A plugin class supplies painters and per-book styles; both are merged into the engine."""

    __slots__ = ()

    @abstractmethod
    def load(self, registry: PainterRegistry, root: Path | None = None) -> dict[str, CoverStyle]:
        """Register every entry-point plugin's painters; return the merged styles by slug."""

    @abstractmethod
    def load_reference(
        self, reference: str, registry: PainterRegistry, root: Path | None = None
    ) -> dict[str, CoverStyle]:
        """Load one plugin from `module:Class`."""
