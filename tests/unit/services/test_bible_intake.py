# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""BibleIntake: a bible's cards are checked together, and the first failed check is the one refused."""

from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.bible_library_interface import BibleLibraryInterface
from engineering_influence.models.bible_file import BibleFile
from engineering_influence.services.bible_card_parser import BibleCardParser
from engineering_influence.services.bible_intake import BibleIntake

REQUIRED = '[required]\ncharacter = ["name"]\n'


def card(kind: str, card_id: str, front: str, body: str = "Prose.") -> BibleFile:
    return BibleFile(kind, card_id, f"+++\n{front}+++\n{body}\n")


class FakeLibrary(BibleLibraryInterface):
    """Returns the files and schema it was given, whatever folder is asked for."""

    def __init__(self, files: tuple[BibleFile, ...], schema: str = "") -> None:
        self._files = files
        self._schema = schema

    def read(self, folder: Path) -> tuple[BibleFile, ...]:
        return self._files

    def schema(self, folder: Path) -> str:
        return self._schema


def intake(*files: BibleFile, schema: str = "") -> tuple:
    return BibleIntake(FakeLibrary(files, schema), BibleCardParser()).intake(Path("bible"))


def refused(*files: BibleFile, schema: str = "") -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        intake(*files, schema=schema)
    return error.value


def test_cards_come_back_sorted_by_kind_and_id() -> None:
    cards = intake(
        card("place", "harbour", ""),
        card("character", "bea", 'name = "Bea"\n'),
        card("character", "ada", 'name = "Ada"\n'),
        schema=REQUIRED,
    )
    assert [(c.kind, c.id) for c in cards] == [
        ("character", "ada"),
        ("character", "bea"),
        ("place", "harbour"),
    ]


def test_a_card_missing_a_required_key_is_refused_with_the_key_named() -> None:
    error = refused(card("character", "ada", 'role = "navigator"\n'), schema=REQUIRED)
    assert error.code == "BIBLE_FIELD_MISSING"
    assert error.message == "character/ada must set name"


def test_a_kind_with_no_required_keys_needs_none() -> None:
    assert len(intake(card("place", "harbour", ""), schema=REQUIRED)) == 1


def test_two_cards_with_one_kind_and_id_are_refused() -> None:
    error = refused(
        card("character", "ada", 'name = "A"\n'), card("character", "ada", 'name = "B"\n')
    )
    assert error.code == "BIBLE_DUPLICATE_ID"


def test_a_link_to_a_card_that_does_not_exist_is_refused() -> None:
    error = refused(card("character", "ada", 'name = "Ada"\n', "Sails to [[place: harbour]]."))
    assert error.code == "BIBLE_LINK_UNKNOWN"
    assert error.message == "character/ada links to place: harbour, which is not a card"


def test_a_link_to_a_card_that_exists_is_allowed() -> None:
    cards = intake(
        card("character", "ada", 'name = "Ada"\n', "Sails to [[place: harbour]]."),
        card("place", "harbour", ""),
    )
    assert len(cards) == 2


def test_a_real_person_must_name_their_clearance() -> None:
    error = refused(card("character", "ada", 'name = "Ada"\nreal = true\nclearance = "  "\n'))
    assert error.code == "BIBLE_REAL_PERSON"
    assert error.message == "character/ada is a real person and must name its clearance"


def test_a_real_person_cannot_carry_a_likeness_or_a_voice() -> None:
    for key in ("likeness", "voice"):
        error = refused(
            card(
                "character",
                "ada",
                f'name = "Ada"\nreal = true\nclearance = "Public record"\n{key} = "x"\n',
            )
        )
        assert error.code == "BIBLE_REAL_PERSON"
        assert "a likeness or a voice cannot be prompted" in error.message


def test_a_real_person_with_clearance_and_no_likeness_or_voice_is_allowed() -> None:
    cards = intake(
        card("character", "ada", 'name = "Ada"\nreal = true\nclearance = "Public record"\n')
    )
    assert cards[0].fields["real"] is True


def test_a_fictional_card_may_carry_a_voice() -> None:
    assert len(intake(card("character", "ada", 'name = "Ada"\nvoice = "low"\n'))) == 1


def test_a_card_that_is_not_a_card_stops_the_intake() -> None:
    assert refused(card("character", "ada", "name = \n")).code == "BIBLE_CARD_INVALID"


def test_an_empty_bible_is_an_empty_tuple() -> None:
    assert intake() == ()
