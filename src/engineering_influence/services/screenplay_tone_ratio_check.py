# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The scene cards' warm-to-conflict ratio: the warm scenes must outnumber the conflict scenes five to one."""

import re
from typing import ClassVar

from engineering_influence.services.interfaces.screenplay_tone_ratio_check_interface import (
    ScreenplayToneRatioCheckInterface,
)


class ScreenplayToneRatioCheck(ScreenplayToneRatioCheckInterface):
    """A card may carry `**Tone:**` with warm, conflict or neutral. When any card carries one, the warm scenes must be
    at least `RATIO` times the conflict scenes: prompt 09 calls the ratio the condition under which the repair scene is
    believable. Cards with no tone are not counted, so a screenplay whose cards carry no tone is not checked."""

    TONES: ClassVar[frozenset[str]] = frozenset({"warm", "conflict", "neutral"})
    RATIO: ClassVar[int] = 5
    CARD: ClassVar[re.Pattern[str]] = re.compile(r"^## S(\d{2,3}) ·", re.MULTILINE)
    TONE: ClassVar[re.Pattern[str]] = re.compile(r"\*\*Tone:\*\*\s*(.*)")

    def problems(self, text: str) -> tuple[str, ...]:
        """Every tone that is not warm, conflict or neutral, then the ratio when conflict scenes are present."""
        tagged = [(number, tone) for number, tone in self._tones(text) if tone is not None]
        found = [
            f"card S{number:02d}: tone {tone!r} is not warm, conflict or neutral"
            for number, tone in tagged
            if tone not in self.TONES
        ]
        warm = sum(1 for _, tone in tagged if tone == "warm")
        conflict = sum(1 for _, tone in tagged if tone == "conflict")
        if conflict and warm < self.RATIO * conflict:
            found.append(
                f"the cards hold {warm} warm scenes to {conflict} conflict scenes; "
                f"warm must be at least {self.RATIO} times conflict"
            )
        return tuple(found)

    @classmethod
    def _tones(cls, text: str) -> list[tuple[int, str | None]]:
        """Each card's number and its tone, or None when the card carries no `**Tone:**` field."""
        starts = list(cls.CARD.finditer(text))
        found: list[tuple[int, str | None]] = []
        for position, match in enumerate(starts):
            end = starts[position + 1].start() if position + 1 < len(starts) else len(text)
            tone = cls.TONE.search(text[match.end() : end])
            found.append((int(match.group(1)), tone.group(1).strip() if tone else None))
        return found
