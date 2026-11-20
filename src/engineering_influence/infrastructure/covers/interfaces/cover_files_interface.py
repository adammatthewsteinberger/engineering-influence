# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CoverFiles."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from PIL import Image


class CoverFilesInterface(ABC):
    """File formats KDP accepts."""

    __slots__ = ()

    @abstractmethod
    def save_tiff(self, img: Image.Image, path: Path, compress: bool = True) -> None:
        """Print panels use lossless Deflate to keep files small; the ebook cover is."""

    @abstractmethod
    def jpeg_bytes(self, img: Image.Image) -> bytes:
        """A high-quality baseline JPEG."""

    @abstractmethod
    def write_pdf(
        self,
        img: Image.Image,
        path: Path,
        width_in: float,
        height_in: float,
        title: str,
        author: str,
    ) -> None:
        """A one-page PDF at KDP's exact cover size, holding the art as one flattened RGB image."""
