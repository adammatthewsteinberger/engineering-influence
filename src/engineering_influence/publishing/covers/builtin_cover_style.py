# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A readable cover style for any book, set in the fonts that ship with the package."""

import zlib
from typing import Any

from engineering_influence.publishing.covers.cover_style import CoverStyle


class BuiltinCoverStyle:
    """Used when no plugin supplies a style for a book's slug."""

    def for_book(self, meta: dict[str, Any]) -> CoverStyle:
        """Derive a style from the book's metadata; the seed comes from its title."""
        title = str(meta["title"]).strip()
        return CoverStyle(
            painter="gradient",
            title_lines=self._lines(title),
            title_font="EBGaramond-SemiBold.otf",
            title_tracking=0.10,
            title_color=(0.97, 0.94, 0.88),
            subtitle_font="EBGaramond-Italic.otf",
            subtitle_color=(0.80, 0.85, 0.93),
            author_font="EBGaramond-Medium.otf",
            author_tracking=0.30,
            author_color=(0.92, 0.88, 0.82),
            body_font="EBGaramond-Regular.otf",
            body_italic="EBGaramond-Italic.otf",
            body_color=(0.94, 0.91, 0.86),
            accent=(0.86, 0.70, 0.40),
            spine_font="EBGaramond-SemiBold.otf",
            spine_color=(0.97, 0.94, 0.88),
            title_frac=0.80,
            seed=zlib.crc32(title.encode("utf-8")) % 100000,
            extra={"subtitle_serif": True, "author_lift_in": 0.06},
        )

    def _lines(self, title: str) -> list[str]:
        words = title.split()
        if len(title) <= 14 or len(words) < 2:
            return [title]
        best = min(
            range(1, len(words)),
            key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))),
        )
        return [" ".join(words[:best]), " ".join(words[best:])]
