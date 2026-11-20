# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The interface a cover plugin implements, discovered through entry points."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.interfaces.cover_painter_interface import CoverPainterInterface
    from engineering_influence.models.covers.cover_style import CoverStyle


class CoverPluginInterface(ABC):
    """Supplies named painters and per-book styles from a private project.

    The loader passes the project root, so a plugin can find project-local source art.
    """

    # The one attribute a plugin has always had; subclasses without slots still get a __dict__.
    __slots__ = ("root",)

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path.cwd()

    @abstractmethod
    def painters(self) -> dict[str, CoverPainterInterface]:
        """Painters by the name a CoverStyle refers to."""

    @abstractmethod
    def styles(self) -> dict[str, CoverStyle]:
        """Cover styles by book slug."""
