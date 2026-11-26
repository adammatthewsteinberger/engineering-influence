# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayAssembler: one Fountain script from the title page and the scenes in order, closed correctly."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.screenplay_assembler import ScreenplayAssembler

SCENE_ONE = "INT. ROOM - DAY\n\nMara waits."
SCENE_TWO = "EXT. PARK - NIGHT\n\nThe dust settles."


def assemble(title_page: tuple[tuple[str, str], ...], scenes: tuple[str, ...]) -> str:
    return ScreenplayAssembler(FountainParser()).assemble(title_page, scenes)


def test_the_script_opens_under_the_title_and_closes_with_the_end() -> None:
    script = assemble((("Title", "MURKY WATER"), ("Author", "Adam")), (SCENE_ONE, SCENE_TWO))
    assert script.startswith("Title: MURKY WATER\nAuthor: Adam\n\nFADE IN:\n\nINT. ROOM - DAY")
    assert script.endswith("EXT. PARK - NIGHT\n\nThe dust settles.\n\nFADE OUT.\n\n>THE END<\n")


def test_the_scenes_keep_their_order() -> None:
    script = assemble((("Title", "X"),), (SCENE_ONE, SCENE_TWO))
    assert script.index("INT. ROOM") < script.index("EXT. PARK")


def test_a_multi_line_value_is_indented_as_fountain_reads_it() -> None:
    script = assemble((("Title", "LIVING\nWATERS"),), (SCENE_ONE,))
    assert "Title: LIVING\n   WATERS" in script


def test_the_title_must_be_named() -> None:
    with pytest.raises(ApplicationError) as error:
        assemble((("Author", "Adam"),), (SCENE_ONE,))
    assert error.value.code == "SCREENPLAY_NO_TITLE"


def test_a_screenplay_has_a_scene() -> None:
    with pytest.raises(ApplicationError) as error:
        assemble((("Title", "X"),), ())
    assert error.value.code == "SCREENPLAY_NO_SCENES"


def test_a_scene_must_be_exactly_one_scene() -> None:
    with pytest.raises(ApplicationError) as error:
        assemble((("Title", "X"),), (SCENE_ONE + "\n\nINT. OTHER - DAY\n\nNo.",))
    assert error.value.code == "SCREENPLAY_SCENE_INVALID"
