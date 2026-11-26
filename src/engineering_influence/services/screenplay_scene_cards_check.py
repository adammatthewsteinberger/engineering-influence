# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The scene cards' mechanical checks: numbering, the fields every card carries, the causal link, beats in order, and
All Is Lost about three-quarters of the way through the cards."""

import re
from typing import ClassVar

from engineering_influence.services.interfaces.screenplay_scene_cards_check_interface import (
    ScreenplaySceneCardsCheckInterface,
)


class ScreenplaySceneCardsCheck(ScreenplaySceneCardsCheckInterface):
    """A card is a `## S01 · heading` section with bullet fields: `**What changes:**`, `**Therefore:**` or `**But:**`
    (not on the last card), `**Beat:**` (one of the fifteen beats), `**Storyline:**` (A, B, M, T or E), and `**Sources:**` (source numbers such as
    `003, 007`).

    What it refuses: card numbers that are not 1, 2, 3 in order; a missing field; a card other than the last with
    neither Therefore nor But; a beat out of order; a storyline outside A, B, M, T, E; and All Is Lost not at
    `ALL_IS_LOST_LOW` to `ALL_IS_LOST_HIGH` of the way through the cards. Whether each link is truly causal stays with a
    reader: prompt 08 asks for causes, and only a person can say whether one is.
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
    STORYLINES: ClassVar[frozenset[str]] = frozenset({"A", "B", "M", "T", "E"})
    ALL_IS_LOST_LOW: ClassVar[float] = 0.70
    ALL_IS_LOST_HIGH: ClassVar[float] = 0.80
    CARD: ClassVar[re.Pattern[str]] = re.compile(r"^## S(\d{2,3}) ·", re.MULTILINE)

    def problems(self, text: str) -> tuple[str, ...]:
        """Every way the cards break the format."""
        cards = self._cards(text)
        if not cards:
            return ("the scene cards need at least one '## S01 · heading' card",)
        found: list[str] = []
        for index, (number, body) in enumerate(cards, 1):
            if number != index:
                found.append(
                    f"card S{number:02d} should be S{index:02d}: the cards run in order from S01"
                )
            found.extend(self._card_problems(number, body, last=index == len(cards)))
        found.extend(self._order_problems(cards))
        return tuple(found)

    def _card_problems(self, number: int, body: str, last: bool) -> list[str]:
        found: list[str] = []
        for field in ("What changes", "Beat", "Storyline", "Sources"):
            if f"**{field}:**" not in body:
                found.append(f"card S{number:02d} has no '**{field}:**' field")
        if not last and "**Therefore:**" not in body and "**But:**" not in body:
            found.append(
                f"card S{number:02d} has no **Therefore:** or **But:** link to the next card"
            )
        storyline = self._field(body, "Storyline")
        if storyline is not None and storyline not in self.STORYLINES:
            found.append(f"card S{number:02d}: storyline {storyline!r} is not A, B, M, T or E")
        sources = self._field(body, "Sources")
        if sources is not None and not re.fullmatch(r"\d{1,3}(\s*,\s*\d{1,3})*", sources):
            found.append(
                f"card S{number:02d}: sources {sources!r} are not source numbers such as 003, 007"
            )
        return found

    def _order_problems(self, cards: tuple[tuple[int, str], ...]) -> list[str]:
        found: list[str] = []
        positions: list[int] = []
        for number, body in cards:
            beat = self._field(body, "Beat")
            if beat is None:
                continue
            if beat not in self.BEATS:
                found.append(f"card S{number:02d}: beat {beat!r} is not one of the fifteen beats")
                continue
            positions.append(self.BEATS.index(beat))
        if positions != sorted(positions):
            found.append("the cards' beats are out of order")
        all_is_lost = [
            i for i, (_, body) in enumerate(cards, 1) if self._field(body, "Beat") == "All Is Lost"
        ]
        if all_is_lost:
            fraction = all_is_lost[0] / len(cards)
            if not self.ALL_IS_LOST_LOW <= fraction <= self.ALL_IS_LOST_HIGH:
                found.append(
                    f"All Is Lost is card {all_is_lost[0]} of {len(cards)} ({fraction:.0%}); it should be about "
                    "three-quarters through"
                )
        return found

    @classmethod
    def _cards(cls, text: str) -> tuple[tuple[int, str], ...]:
        """Each card's number and the text under its heading, up to the next card."""
        starts = list(cls.CARD.finditer(text))
        cards: list[tuple[int, str]] = []
        for position, match in enumerate(starts):
            end = starts[position + 1].start() if position + 1 < len(starts) else len(text)
            cards.append((int(match.group(1)), text[match.end() : end]))
        return tuple(cards)

    @staticmethod
    def _field(body: str, field: str) -> str | None:
        """The text after a `**Field:**` label on its line, or None when the label is absent."""
        match = re.search(rf"\*\*{field}:\*\*\s*(.*)", body)
        return match.group(1).strip() if match else None
