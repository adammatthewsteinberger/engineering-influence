# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The beat sheet's mechanical checks: the fifteen beats in order, page ranges that move forward within the film,
a relationship function from the fixed set, and All Is Lost about three-quarters of the way through."""

from typing import ClassVar

from engineering_influence.services.interfaces.screenplay_beat_sheet_check_interface import (
    ScreenplayBeatSheetCheckInterface,
)


class ScreenplayBeatSheetCheck(ScreenplayBeatSheetCheckInterface):
    """The beat sheet is a markdown table with six cells: Beat | Pages | Scenes | Scene | Central character | Function.

    Pages are written `a to b`. What it refuses: a missing or repeated beat, beats out of order, a range that runs
    backwards, a range that starts before the one before it, a range past the film's last page, a function outside the
    fixed set, and an All Is Lost that does not start between `ALL_IS_LOST_LOW` and `ALL_IS_LOST_HIGH` of the way
    through the film.
    """

    BEATS: ClassVar[tuple[str, ...]] = (
        "Opening Image",
        "Theme Stated",
        "Set-Up",
        "Catalyst",
        "Debate",
        "Break into Two",
        "B Story",
        "Fun and Games",
        "Midpoint",
        "Bad Guys Close In",
        "All Is Lost",
        "Dark Night of the Soul",
        "Break into Three",
        "Finale",
        "Closing Image",
    )
    FUNCTIONS: ClassVar[frozenset[str]] = frozenset(
        {
            "social penetration layer advance",
            "vulnerability leap",
            "oxytocin loop",
            "rupture",
            "repair",
            "none",
        }
    )
    ALL_IS_LOST_LOW: ClassVar[float] = 0.70
    ALL_IS_LOST_HIGH: ClassVar[float] = 0.80

    def __init__(self, target_pages: int) -> None:
        if target_pages < 1:
            raise ValueError("a film has a positive number of pages")
        self._target = target_pages

    def problems(self, text: str) -> tuple[str, ...]:
        """Every way the beat sheet breaks the format."""
        rows = self._rows(text)
        names = tuple(name for name, _ in rows)
        if names != self.BEATS:
            return (f"the beat sheet needs the fifteen beats in order; it has {len(rows)} rows",)
        found: list[str] = []
        previous_start = 0
        for name, cells in rows:
            pages = cells[1]
            start, end = self._range(pages)
            if start is None or end is None or start > end:
                found.append(
                    f"{name}: the pages {pages!r} are not a range 'a to b' with a not after b"
                )
                continue
            if start < previous_start:
                found.append(f"{name}: starts at page {start}, before the beat above it")
            if end > self._target:
                found.append(f"{name}: ends at page {end}, past the film's {self._target} pages")
            previous_start = start
            if cells[5].lower() not in self.FUNCTIONS:
                found.append(
                    f"{name}: relationship function {cells[5]!r} is not one of the fixed set"
                )
            if name == "All Is Lost" and start is not None:
                fraction = start / self._target
                if not self.ALL_IS_LOST_LOW <= fraction <= self.ALL_IS_LOST_HIGH:
                    found.append(
                        f"All Is Lost starts at {fraction:.0%} of the film; it should be about three-quarters"
                    )
        return tuple(found)

    @classmethod
    def _rows(cls, text: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """The table rows whose first cell is a beat name, with all six cells."""
        rows: list[tuple[str, tuple[str, ...]]] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            cells = tuple(cell.strip() for cell in stripped.strip("|").split("|"))
            if len(cells) == 6 and cells[0] in cls.BEATS:
                rows.append((cells[0], cells))
        return tuple(rows)

    @staticmethod
    def _range(pages: str) -> tuple[int | None, int | None]:
        """`a to b` as two page numbers, or None for each part that is not a number."""
        parts = pages.split(" to ")
        if len(parts) != 2:
            return None, None
        start, end = parts[0].strip(), parts[1].strip()
        return (int(start) if start.isdigit() else None, int(end) if end.isdigit() else None)
