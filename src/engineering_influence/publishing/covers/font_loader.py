"""Loads cover fonts by file name from a search path."""

import math
from collections.abc import Sequence
from pathlib import Path

from PIL import ImageFont

from engineering_influence.publishing.typesetting.book_build_error import BookBuildError


class FontLoader:
    """The first directory that holds the file wins."""

    def __init__(self, directories: Sequence[Path]) -> None:
        self._directories = list(directories)

    def load(self, name: str, size_px: float) -> ImageFont.FreeTypeFont:
        """Load a font at a pixel size (rounded up, minimum 6)."""
        size = max(6, math.ceil(size_px - 1e-6))
        for directory in self._directories:
            path = directory / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
        raise BookBuildError(f"cover font not found: {name}")
