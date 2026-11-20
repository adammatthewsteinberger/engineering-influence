# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for KdpGeometry."""

from abc import ABC, abstractmethod


class KdpGeometryInterface(ABC):
    """Trim size, margins, and page-count-dependent gutter for a 6 x 9 in interior."""

    __slots__ = ()

    @abstractmethod
    def gutter_inches(self, pages: int) -> float:
        """Return the minimum gutter in inches for a book of the given page count."""
