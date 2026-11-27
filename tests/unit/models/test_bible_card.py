# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""BibleCard: its links are the `[[kind: id]]` pairs in its body, and only well-formed ones count."""

import pytest

from engineering_influence.models.bible_card import BibleCard


def test_links_are_the_well_formed_pairs_in_the_body_in_order() -> None:
    card = BibleCard(
        "scene",
        "harbour-storm",
        {"title": "Storm"},
        "[[character: ada]] goes to [[place: harbour-1]]. A [[bad]] link and a [[Place: x]] do not count.",
    )
    assert card.links() == (("character", "ada"), ("place", "harbour-1"))


def test_a_card_with_no_links_has_none() -> None:
    assert BibleCard("place", "harbour", {}, "Plain prose.").links() == ()


@pytest.mark.parametrize(("kind", "card_id"), [("Place", "harbour"), ("place", "Harbour")])
def test_a_card_must_have_a_lowercase_kind_and_id(kind: str, card_id: str) -> None:
    with pytest.raises(ValueError, match="bible"):
        BibleCard(kind, card_id, {}, "")
