# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayDraftingOrder: the images and All Is Lost first, then the rest in card order, the likely-shared scenes last."""

import pytest

from engineering_influence.services.screenplay_drafting_order import ScreenplayDraftingOrder

CARDS = (
    (1, "Opening Image"),
    (2, "Set-Up"),
    (3, "Catalyst"),
    (4, "Fun and Games"),
    (5, "All Is Lost"),
    (6, "Dark Night of the Soul"),
    (7, "Closing Image"),
    (8, "Finale"),
)


def test_images_and_all_is_lost_come_first_then_the_rest_in_card_order() -> None:
    assert ScreenplayDraftingOrder().order(CARDS, frozenset()) == (1, 7, 5, 2, 3, 4, 6, 8)


def test_the_likely_shared_scenes_are_drafted_last() -> None:
    assert ScreenplayDraftingOrder().order(CARDS, frozenset({4, 8})) == (1, 7, 5, 2, 3, 6, 4, 8)


def test_a_repeated_card_number_is_refused() -> None:
    with pytest.raises(ValueError, match="number of its own"):
        ScreenplayDraftingOrder().order(((1, "Set-Up"), (1, "Finale")), frozenset())


def test_a_shareable_scene_must_be_a_card() -> None:
    with pytest.raises(ValueError, match="must be one of the cards"):
        ScreenplayDraftingOrder().order(CARDS, frozenset({99}))
