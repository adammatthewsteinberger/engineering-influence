# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FountainScene: numbered from 1, with a heading, its notes and its elements."""

import pytest

from engineering_influence.models.fountain_block import FountainBlock
from engineering_influence.models.fountain_scene import FountainScene


def scene(number: int = 1, heading: str = "INT. ROOM - DAY") -> FountainScene:
    return FountainScene(
        number, heading, (("set", "hab1-bunk-room"),), (FountainBlock("action", ("Mara waits.",)),)
    )


def test_a_scene_text_is_its_heading_and_elements() -> None:
    assert scene().text() == "INT. ROOM - DAY\nMara waits."


def test_a_note_is_found_by_key_or_is_none() -> None:
    assert scene().note("set") == "hab1-bunk-room"
    assert scene().note("sol") is None


def test_scenes_are_numbered_from_one() -> None:
    with pytest.raises(ValueError, match="numbered from 1"):
        scene(number=0)


def test_a_scene_has_a_heading() -> None:
    with pytest.raises(ValueError, match="has a heading"):
        scene(heading="   ")
