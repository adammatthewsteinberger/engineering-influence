# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ShootingScriptRenderer: each scene's number goes on its heading, an omitted scene keeps its place as a forced heading,
and the rest of the script is kept as written."""

import pytest

from engineering_influence.models.shooting_lock import ShootingLock
from engineering_influence.models.shooting_lock_entry import ShootingLockEntry
from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.shooting_script_renderer import ShootingScriptRenderer

RENDERER = ShootingScriptRenderer(FountainParser())
SCRIPT = "Title: FILM\n\nFADE IN:\n\nINT. ROOM - DAY\n\nFirst.\n\nEXT. YARD - NIGHT\n\nSecond.\n\nFADE OUT.\n"
ONE_SCENE = "INT. ROOM - DAY\n\nFirst.\n"


def lock(*rows: tuple[int, str, bool]) -> ShootingLock:
    return ShootingLock(
        tuple(ShootingLockEntry(card, label, omitted) for card, label, omitted in rows)
    )


def test_each_heading_gets_its_number_at_the_end() -> None:
    rendered = RENDERER.render(SCRIPT, (1, 2), lock((1, "1", False), (2, "42A", False)))
    assert "INT. ROOM - DAY #1#\n" in rendered
    assert "EXT. YARD - NIGHT #42A#\n" in rendered


def test_the_title_page_and_the_text_between_scenes_are_kept() -> None:
    rendered = RENDERER.render(SCRIPT, (1, 2), lock((1, "1", False), (2, "2", False)))
    assert rendered.startswith("Title: FILM\n\nFADE IN:\n\nINT. ROOM - DAY #1#\n\nFirst.")
    assert rendered.endswith("Second.\n\nFADE OUT.\n")


def test_an_omitted_scene_is_a_forced_heading_in_its_place() -> None:
    rendered = RENDERER.render(ONE_SCENE, (1,), lock((1, "1", False), (2, "2", True)))
    assert rendered == "INT. ROOM - DAY #1#\n\nFirst.\n\n.OMITTED #2#\n"


def test_boneyard_comments_are_taken_out() -> None:
    rendered = RENDERER.render(
        "INT. ROOM - DAY\n\n/* a note for the writer */\n\nFirst.\n", (1,), lock((1, "1", False))
    )
    assert "note for the writer" not in rendered


def test_a_script_with_another_number_of_scenes_is_refused() -> None:
    with pytest.raises(ValueError, match="each scene card is one scene"):
        RENDERER.render(ONE_SCENE, (1, 2), lock((1, "1", False), (2, "2", False)))
