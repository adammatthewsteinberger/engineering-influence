# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The assembled script's beat positions: each beat sits where the beat sheet puts it, measured in the script's length."""

from typing import ClassVar

from engineering_influence.services.interfaces.fountain_page_estimate_interface import (
    FountainPageEstimateInterface,
)
from engineering_influence.services.interfaces.screenplay_beat_position_check_interface import (
    ScreenplayBeatPositionCheckInterface,
)
from engineering_influence.services.screenplay_beat_sheet_check import ScreenplayBeatSheetCheck


class ScreenplayBeatPositionCheck(ScreenplayBeatPositionCheckInterface):
    """Each beat is placed as a fraction of the way through the script: the first scene card tagged with it begins
    where the beat sheet says, to within ALLOWED_DRIFT of the film. The script's own length is measured, not the card
    count, so a long opening scene moves every beat after it.

    What it refuses: a beat of the beat sheet that no scene card is tagged with, and a beat that begins further from
    its planned place than ALLOWED_DRIFT. A card tagged with a name that is not one of the fifteen is left to the
    scene-cards check, which already refuses it.
    """

    ALLOWED_DRIFT: ClassVar[float] = 0.05

    def __init__(self, estimate: FountainPageEstimateInterface, target_pages: int) -> None:
        if target_pages < 1:
            raise ValueError("a film has a positive number of pages")
        self._estimate = estimate
        self._target = target_pages

    def problems(self, beat_sheet: str, scenes: tuple[tuple[str, str], ...]) -> tuple[str, ...]:
        """Every beat that is missing from the script or begins out of place."""
        planned = ScreenplayBeatSheetCheck.planned_starts(beat_sheet)
        lines = tuple(self._estimate.lines(text) for _, text in scenes)
        first = self._first_fractions(scenes, lines)
        found: list[str] = []
        for beat in ScreenplayBeatSheetCheck.BEATS:
            if beat not in planned:
                continue
            if beat not in first:
                found.append(f"{beat}: no scene card is tagged with it")
                continue
            expected = (planned[beat] - 1) / self._target
            actual = first[beat]
            if abs(actual - expected) > self.ALLOWED_DRIFT:
                found.append(
                    f"{beat} begins {actual:.0%} of the way through the script; the beat sheet puts it at "
                    f"{expected:.0%}"
                )
        return tuple(found)

    @staticmethod
    def _first_fractions(
        scenes: tuple[tuple[str, str], ...], lines: tuple[int, ...]
    ) -> dict[str, float]:
        """For each beat, the fraction of the script's lines that come before its first scene."""
        total = sum(lines)
        first: dict[str, float] = {}
        before = 0
        for (beat, _), count in zip(scenes, lines, strict=True):
            first.setdefault(beat, before / total)
            before += count
        return first
