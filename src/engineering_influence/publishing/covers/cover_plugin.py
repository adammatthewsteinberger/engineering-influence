"""The interface a cover plugin implements, discovered through entry points."""

from abc import ABC, abstractmethod

from engineering_influence.publishing.covers.cover_painter import CoverPainter
from engineering_influence.publishing.covers.cover_style import CoverStyle


class CoverPlugin(ABC):
    """Supplies named painters and per-book styles from a private project."""

    @abstractmethod
    def painters(self) -> dict[str, CoverPainter]:
        """Painters by the name a CoverStyle refers to."""

    @abstractmethod
    def styles(self) -> dict[str, CoverStyle]:
        """Cover styles by book slug."""
