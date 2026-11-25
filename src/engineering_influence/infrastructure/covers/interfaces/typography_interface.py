# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Typography."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import ImageDraw, ImageFont

    from engineering_influence.models.covers.cover_layout import CoverLayout


class TypographyInterface(ABC):
    """Tracked (letter-spaced) text, fitting, wrapping, and the print size floor."""

    __slots__ = ()

    @abstractmethod
    def font(self, name: str, size_px: float) -> ImageFont.FreeTypeFont:
        """Load a font."""

    @abstractmethod
    def floor_px(self, layout: CoverLayout, size_px: float) -> float:
        """Raise a print text size to the floor; ebook covers are not printed."""

    @abstractmethod
    def c8(self, color: tuple[float, float, float]) -> tuple[int, int, int, int]:
        """A 0..1 colour as an opaque 8-bit RGBA tuple."""

    @abstractmethod
    def tracked_width(self, f: ImageFont.FreeTypeFont, text: str, tracking_px: float) -> float:
        """Width of text with extra spacing between characters."""

    @abstractmethod
    def draw_tracked(
        self,
        draw: ImageDraw.ImageDraw,
        xy: tuple[float, float],
        text: str,
        f: ImageFont.FreeTypeFont,
        fill: tuple[int, int, int, int],
        tracking_px: float,
    ) -> None:
        """Draw tracked text and record its size."""

    @abstractmethod
    def fit_size(
        self, fontname: str, lines: list[str], tracking_em: float, width_px: float
    ) -> float:
        """The font size at which the widest line is `width_px` wide."""

    @abstractmethod
    def cap_top(self, f: ImageFont.FreeTypeFont, text: str) -> int:
        """The offset from the draw origin to the top of the text's ink."""

    @abstractmethod
    def wrap_px(
        self, text: str, f: ImageFont.FreeTypeFont, width: float, tracking: float = 0
    ) -> list[str]:
        """Greedy word wrap to a pixel width."""

    @abstractmethod
    def plain(self, md: str) -> str:
        """Strip Markdown emphasis markers."""
