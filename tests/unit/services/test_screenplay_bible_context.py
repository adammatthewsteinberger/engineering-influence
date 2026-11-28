# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayBibleContext: a stored card reaches a scene only when the scene names it."""

from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.models.bible_card import BibleCard
from engineering_influence.services.screenplay_bible_context import ScreenplayBibleContext


def store_card(store: InMemoryArtifactStore, card: BibleCard) -> None:
    store.put("run-1", card.artifact(), card.encode().encode("utf-8"))


def test_a_card_is_named_by_its_name_field_whatever_the_case() -> None:
    store = InMemoryArtifactStore()
    store_card(
        store,
        BibleCard(
            "character", "ada", {"name": "Ada Lovelace", "role": "navigator"}, "Keeps the log."
        ),
    )
    block = ScreenplayBibleContext(store).for_scene("run-1", "ADA LOVELACE climbs the mast.")
    assert block == "Bible character/ada:\nname: Ada Lovelace\nrole: navigator\nKeeps the log."


def test_a_card_is_named_by_its_id_with_hyphens_read_as_spaces() -> None:
    store = InMemoryArtifactStore()
    store_card(store, BibleCard("place", "harbour-wall", {}, "A wall of stone."))
    assert "harbour-wall" in ScreenplayBibleContext(store).for_scene(
        "run-1", "At the harbour wall, dawn."
    )


def test_a_name_must_be_whole_words_not_part_of_a_longer_word() -> None:
    store = InMemoryArtifactStore()
    store_card(store, BibleCard("character", "ada", {"name": "Ada"}, "Keeps the log."))
    assert ScreenplayBibleContext(store).for_scene("run-1", "Adams walks in.") == ""


def test_a_card_the_scene_does_not_name_is_left_out() -> None:
    store = InMemoryArtifactStore()
    store_card(store, BibleCard("character", "bea", {"name": "Bea"}, "Cooks."))
    assert ScreenplayBibleContext(store).for_scene("run-1", "Nobody here.") == ""


def test_a_blank_name_falls_back_to_the_id_and_other_artifacts_are_ignored() -> None:
    store = InMemoryArtifactStore()
    store_card(store, BibleCard("character", "ada", {"name": "   "}, "Keeps the log."))
    store.put("run-1", "source/001.md", b"Ada sails.")
    assert "Bible character/ada:" in ScreenplayBibleContext(store).for_scene("run-1", "Ada sails.")
    assert ScreenplayBibleContext(store).for_scene("run-1", "Nothing here.") == ""


def test_a_name_whose_artifact_has_gone_is_skipped() -> None:
    class Vanished(InMemoryArtifactStore):
        def get(self, run_id: str, name: str) -> bytes | None:
            return None

    store = Vanished()
    store_card(store, BibleCard("character", "ada", {"name": "Ada"}, "Keeps the log."))
    assert ScreenplayBibleContext(store).for_scene("run-1", "Ada sails.") == ""
