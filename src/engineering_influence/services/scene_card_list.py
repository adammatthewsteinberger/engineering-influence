# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads the scene cards of the scene_cards artifact: each card's number, its beat and its text."""

import re
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.scene_card import SceneCard
from engineering_influence.services.interfaces.scene_card_list_interface import (
    SceneCardListInterface,
)


class SceneCardList(SceneCardListInterface):
    """A card starts at `## S01 · heading` and carries a `**Beat:**` field and a `**Sources:**` field of source numbers.
    A card without a beat or sources, or no card at all, is refused as unreadable: a scene cannot be drafted under no
    beat, nor from no source."""

    CARD: ClassVar[re.Pattern[str]] = re.compile(r"^## S(\d{2,3}) ·", re.MULTILINE)
    BEAT: ClassVar[re.Pattern[str]] = re.compile(r"\*\*Beat:\*\*\s*(.+)")
    SOURCES: ClassVar[re.Pattern[str]] = re.compile(r"\*\*Sources:\*\*\s*(.+)")

    def parse(self, text: str) -> tuple[SceneCard, ...]:
        """Every card, in the order the text gives them."""
        starts = list(self.CARD.finditer(text))
        if not starts:
            raise ApplicationError(
                code="SCENE_CARDS_UNREADABLE",
                message="the scene cards have no '## S01 ·' card",
                http_status=422,
            )
        cards: list[SceneCard] = []
        for position, match in enumerate(starts):
            end = starts[position + 1].start() if position + 1 < len(starts) else len(text)
            body = text[match.start() : end].strip()
            beat = self.BEAT.search(body)
            if beat is None:
                raise ApplicationError(
                    code="SCENE_CARDS_UNREADABLE",
                    message=f"scene card S{match.group(1)} has no '**Beat:**' field",
                    http_status=422,
                )
            cited = self.SOURCES.search(body)
            numbers = tuple(int(n) for n in re.findall(r"\d+", cited.group(1))) if cited else ()
            if not numbers:
                raise ApplicationError(
                    code="SCENE_CARDS_UNREADABLE",
                    message=f"scene card S{match.group(1)} has no '**Sources:**' field with source numbers",
                    http_status=422,
                )
            cards.append(SceneCard(int(match.group(1)), beat.group(1).strip(), body, numbers))
        return tuple(cards)
