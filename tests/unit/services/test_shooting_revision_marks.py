# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ShootingRevisionMarks: a revised scene is matched to its baseline by number, and marked as the revision's colour when its text changed."""

import pytest

from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.shooting_revision_marks import ShootingRevisionMarks

BASELINE = "FADE IN:\n\nINT. ROOM - DAY #1#\n\nAda waits.\n\nEXT. YARD - NIGHT #2#\n\nRain falls.\n"


def marks(script: str, revision: int = 1) -> str:
    return ShootingRevisionMarks(FountainParser()).mark(BASELINE, script, revision)


def test_an_unchanged_scene_gets_no_mark() -> None:
    assert "[[revised" not in marks(BASELINE)


def test_a_scene_whose_text_changed_is_marked_above_its_heading() -> None:
    changed = BASELINE.replace("Ada waits.", "Ada waits longer.")
    assert "[[revised: Blue *]]\nINT. ROOM - DAY #1#\n\nAda waits longer." in marks(changed)


def test_a_scene_with_a_new_number_is_marked_as_new() -> None:
    added = BASELINE + "\nINT. HALL - DAY #2A#\n\nA door opens.\n"
    result = marks(added)
    assert "[[revised: Blue *]]\nINT. HALL - DAY #2A#" in result
    assert result.count("[[revised") == 1


def test_a_scene_that_moved_its_place_but_not_its_text_is_unchanged() -> None:
    reordered = (
        "FADE IN:\n\nEXT. YARD - NIGHT #2#\n\nRain falls.\n\nINT. ROOM - DAY #1#\n\nAda waits.\n"
    )
    assert "[[revised" not in marks(reordered)


def test_the_revision_number_picks_the_colour_in_order() -> None:
    changed = BASELINE.replace("Rain falls.", "Rain stops.")
    assert "[[revised: Pink *]]" in marks(changed, revision=2)


def test_a_revision_outside_the_colours_is_refused() -> None:
    with pytest.raises(ValueError, match="a revision is numbered 1 to 9, not 0"):
        marks(BASELINE, revision=0)


def test_a_scene_without_a_number_is_refused() -> None:
    with pytest.raises(ValueError, match="a scene has no number"):
        marks("INT. ROOM - DAY\n\nNo number here.\n")
