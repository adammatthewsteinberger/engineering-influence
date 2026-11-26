# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SceneCardList: each card carries its beat and the numbers of the source files it draws on; a card without either is
unreadable."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.scene_card import SceneCard
from engineering_influence.services.scene_card_list import SceneCardList

CARD = "## S{n:02d} · a scene\n**What changes:** it changes.\n**Beat:** Set-Up\n**Sources:** {sources}\n"


def test_each_card_gives_its_number_its_beat_and_its_sources() -> None:
    text = CARD.format(n=1, sources="003, 007") + CARD.format(n=2, sources="12")
    first, second = SceneCardList().parse(text)
    assert (first.number, first.beat, first.sources) == (1, "Set-Up", (3, 7))
    assert second.sources == (12,)


def test_a_card_with_no_sources_field_is_unreadable() -> None:
    text = "## S01 · a scene\n**What changes:** it changes.\n**Beat:** Set-Up\n"
    with pytest.raises(ApplicationError) as error:
        SceneCardList().parse(text)
    assert error.value.code == "SCENE_CARDS_UNREADABLE"


def test_a_sources_field_with_no_numbers_is_unreadable() -> None:
    with pytest.raises(ApplicationError) as error:
        SceneCardList().parse(CARD.format(n=1, sources="the first file"))
    assert error.value.code == "SCENE_CARDS_UNREADABLE"


def test_a_card_must_name_at_least_one_source_numbered_from_one() -> None:
    with pytest.raises(ValueError):
        SceneCard(1, "Set-Up", "body", ())
    with pytest.raises(ValueError):
        SceneCard(1, "Set-Up", "body", (0,))
