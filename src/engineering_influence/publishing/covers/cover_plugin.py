"""The interface a cover plugin implements, discovered through entry points."""

from abc import ABC, abstractmethod
from pathlib import Path

from engineering_influence.publishing.covers.cover_painter import CoverPainter
from engineering_influence.publishing.covers.cover_style import CoverStyle


class CoverPlugin(ABC):
    """Supplies named painters and per-book styles from a private project.

    The loader passes the project root, so a plugin can find project-local source art.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path.cwd()

    @abstractmethod
    def painters(self) -> dict[str, CoverPainter]:
        """Painters by the name a CoverStyle refers to."""

    @abstractmethod
    def styles(self) -> dict[str, CoverStyle]:
        """Cover styles by book slug."""
