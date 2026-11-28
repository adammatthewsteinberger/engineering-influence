# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""BibleCardParser: a card's front matter is TOML between two +++ lines, and bible.toml names the required keys."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.bible_file import BibleFile
from engineering_influence.services.bible_card_parser import BibleCardParser


def test_a_card_reads_its_front_matter_and_trimmed_body() -> None:
    text = '+++\nname = "Ada"\nreal = false\n+++\n\nAda sails at dawn.\n\n'
    card = BibleCardParser().card(BibleFile("character", "ada", text))
    assert card.kind == "character"
    assert card.id == "ada"
    assert card.fields == {"name": "Ada", "real": False}
    assert card.body == "Ada sails at dawn."


def test_a_card_with_empty_front_matter_has_no_fields() -> None:
    card = BibleCardParser().card(BibleFile("place", "harbour", "+++\n+++\nThe harbour."))
    assert card.fields == {}


@pytest.mark.parametrize(
    "text",
    [
        'name = "Ada"\n+++\n',  # no opening line
        "",  # no lines at all
        '+++\nname = "Ada"\n',  # no closing line
        "+++\nname = \n+++\n",  # front matter that is not TOML
    ],
)
def test_a_card_whose_front_matter_is_wrong_is_refused(text: str) -> None:
    with pytest.raises(ApplicationError) as error:
        BibleCardParser().card(BibleFile("character", "ada", text))
    assert error.value.code == "BIBLE_CARD_INVALID"
    assert error.value.message.startswith("character/ada.md: ")


def test_an_empty_schema_requires_nothing() -> None:
    assert BibleCardParser().schema("") == {}
    assert BibleCardParser().schema("   \n") == {}


def test_the_required_table_maps_each_kind_to_its_keys() -> None:
    schema = BibleCardParser().schema(
        '[required]\ncharacter = ["name", "role"]\nplace = ["name"]\n'
    )
    assert schema == {"character": ("name", "role"), "place": ("name",)}


def test_a_schema_with_no_required_table_requires_nothing() -> None:
    assert BibleCardParser().schema("# nothing required yet\n") == {}


@pytest.mark.parametrize(
    "text",
    [
        '[other]\ncharacter = ["name"]\n',  # a table that is not [required]
        "required = 3\n",  # [required] is not a table
        'character = "name"\n',  # a kind's keys are not a list
        '[required]\ncharacter = ["name", 1]\n',  # a key that is not text
        "[required\n",  # not TOML
    ],
)
def test_a_malformed_schema_is_refused(text: str) -> None:
    with pytest.raises(ApplicationError) as error:
        BibleCardParser().schema(text)
    assert error.value.code == "BIBLE_SCHEMA_INVALID"
