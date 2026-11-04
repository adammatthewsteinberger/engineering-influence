"""How one book's cover is painted and typeset."""

from dataclasses import dataclass, field
from typing import Any

Color = tuple[float, float, float]


@dataclass
class CoverStyle:
    """Palette, type, and painter choice. Font names are files found by the FontLoader."""

    painter: str
    title_lines: list[str]
    title_font: str
    title_tracking: float  # em
    title_color: Color
    subtitle_font: str
    subtitle_color: Color
    author_font: str
    author_tracking: float
    author_color: Color
    body_font: str
    body_italic: str
    body_color: Color
    accent: Color
    spine_font: str
    spine_color: Color
    title_frac: float = 0.86  # title block width as a fraction of the safe width
    title_case_upper: bool = True
    author_on_top: bool = False
    title_top: float = 0.0  # title block offset, fraction of safe height
    seed: int = 1
    extra: dict[str, Any] = field(default_factory=dict)
