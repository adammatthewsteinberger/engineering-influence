# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Bible intake: a bible's cards, checked together. Required keys, unique ids, links that land on a card, and real people."""

from pathlib import Path
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.bible_library_interface import BibleLibraryInterface
from engineering_influence.models.bible_card import BibleCard
from engineering_influence.services.interfaces.bible_card_parser_interface import (
    BibleCardParserInterface,
)
from engineering_influence.services.interfaces.bible_intake_interface import BibleIntakeInterface


class BibleIntake(BibleIntakeInterface):
    """Every check needs the whole bible at once: a link is valid only if its card exists, and an id is unique only among
    the cards. So the cards are all read first, and only then checked (ADR 0018)."""

    FORBIDDEN_FOR_REAL: ClassVar[tuple[str, ...]] = ("likeness", "voice")

    def __init__(self, library: BibleLibraryInterface, parser: BibleCardParserInterface) -> None:
        """Remember the bible library and the card parser; checks look at the whole bible at once."""
        self._library = library
        self._parser = parser

    def intake(self, folder: Path) -> tuple[BibleCard, ...]:
        """The cards in kind and id order. The first failed check is the one raised."""
        schema = self._parser.schema(self._library.schema(folder))
        cards = sorted(
            (self._parser.card(file) for file in self._library.read(folder)),
            key=lambda card: (card.kind, card.id),
        )
        known: set[tuple[str, str]] = set()
        for card in cards:
            if (card.kind, card.id) in known:
                raise ApplicationError(
                    code="BIBLE_DUPLICATE_ID",
                    message=f"two cards are {card.kind}/{card.id}: an id is unique within its kind",
                    http_status=422,
                )
            known.add((card.kind, card.id))
            self._check_card(card, schema)
        for card in cards:
            for kind, card_id in card.links():
                if (kind, card_id) not in known:
                    raise ApplicationError(
                        code="BIBLE_LINK_UNKNOWN",
                        message=f"{card.kind}/{card.id} links to {kind}: {card_id}, which is not a card",
                        http_status=422,
                    )
        return tuple(cards)

    def _check_card(self, card: BibleCard, schema: dict[str, tuple[str, ...]]) -> None:
        path = f"{card.kind}/{card.id}"
        missing = [key for key in schema.get(card.kind, ()) if key not in card.fields]
        if missing:
            raise ApplicationError(
                code="BIBLE_FIELD_MISSING",
                message=f"{path} must set {', '.join(missing)}",
                http_status=422,
            )
        if card.fields.get("real") is True:
            if not str(card.fields.get("clearance", "")).strip():
                raise self._real_person(f"{path} is a real person and must name its clearance")
            if any(key in card.fields for key in self.FORBIDDEN_FOR_REAL):
                raise self._real_person(
                    f"{path} is a real person: a likeness or a voice cannot be prompted"
                )

    @staticmethod
    def _real_person(message: str) -> ApplicationError:
        return ApplicationError(code="BIBLE_REAL_PERSON", message=message, http_status=422)
