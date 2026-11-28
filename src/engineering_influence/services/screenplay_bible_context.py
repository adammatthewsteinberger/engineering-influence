# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The bible cards a scene needs: the stored cards whose name appears in the scene's text. Nothing else is sent."""

import re

from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.models.bible_card import BibleCard
from engineering_influence.services.interfaces.screenplay_bible_context_interface import (
    ScreenplayBibleContextInterface,
)


class ScreenplayBibleContext(ScreenplayBibleContextInterface):
    """A card is named when its name field, or its id with hyphens read as spaces, appears as whole words in the text.
    Matching is case-blind, so the bible's spelling is the only one that has to be right."""

    def __init__(self, artifacts: ArtifactStoreInterface) -> None:
        """Remember the artifacts the bible cards are read from."""
        self._artifacts = artifacts

    def for_scene(self, run_id: str, text: str) -> str:
        """Each named card as a block: its kind and id, its fields one per line, then its body."""
        blocks: list[str] = []
        for name in sorted(self._artifacts.names(run_id)):
            if not name.startswith("bible/"):
                continue
            data = self._artifacts.get(run_id, name)
            if data is None:
                continue
            card = BibleCard.decode(data.decode("utf-8"))
            if self._named(card, text):
                blocks.append(self._block(card))
        return "\n\n".join(blocks)

    @staticmethod
    def _named(card: BibleCard, text: str) -> bool:
        names = {card.id.replace("-", " ")}
        name = card.fields.get("name")
        if isinstance(name, str) and name.strip():
            names.add(name.strip())
        return any(
            re.search(rf"\b{re.escape(candidate)}\b", text, re.IGNORECASE) for candidate in names
        )

    @staticmethod
    def _block(card: BibleCard) -> str:
        fields = "\n".join(f"{key}: {value}" for key, value in card.fields.items())
        return f"Bible {card.kind}/{card.id}:\n{fields}\n{card.body}".rstrip()
