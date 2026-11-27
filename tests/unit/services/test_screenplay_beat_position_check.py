# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayBeatPositionCheck: each beat's first scene sits where the beat sheet puts it, measured in the script's length."""

import pytest

from engineering_influence.services.fountain_page_estimate import FountainPageEstimate
from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.screenplay_beat_position_check import (
    ScreenplayBeatPositionCheck,
)
from engineering_influence.services.screenplay_beat_sheet_check import ScreenplayBeatSheetCheck

BEATS = ScreenplayBeatSheetCheck.BEATS
SCENE = "INT. ROOM - DAY\n\nA scene plays out."


def check(target: int) -> ScreenplayBeatPositionCheck:
    return ScreenplayBeatPositionCheck(FountainPageEstimate(FountainParser()), target)


def scenes(*beats: str, text: str = SCENE) -> tuple[tuple[str, str], ...]:
    """One scene per beat, each the same size, so that a beat's place is its card's place in the list."""
    return tuple((beat, text) for beat in beats)


def sheet(starts: dict[str, int] | None = None) -> str:
    """A beat sheet with each beat planned at the page given, or at its place in the list (1 to 15) by default."""
    rows = [
        "| Beat | Pages | Scenes | Scene | Central character | Function |",
        "|---|---|---|---|---|---|",
    ]
    for index, beat in enumerate(BEATS, 1):
        page = (starts or {}).get(beat, index)
        rows.append(f"| {beat} | {page} to {page} | 1 | scene | character | none |")
    return "\n".join(rows) + "\n"


def proportional(target: int) -> dict[str, int]:
    """Each beat planned where its card falls in a list of fifteen, scaled to a film of the target's pages."""
    return {beat: round(index * target / 15) + 1 for index, beat in enumerate(BEATS)}


def test_a_script_whose_beats_fall_where_the_sheet_puts_them_has_no_problems() -> None:
    assert check(15).problems(sheet(), scenes(*BEATS)) == ()


def test_a_beat_that_begins_late_is_named_with_both_positions() -> None:
    # All Is Lost is the eleventh of fifteen scenes (67%); the sheet plans it on page 14 (87%).
    found = check(15).problems(sheet({"All Is Lost": 14}), scenes(*BEATS))
    assert found == (
        "All Is Lost begins 67% of the way through the script; the beat sheet puts it at 87%",
    )


def test_a_beat_within_five_per_cent_of_the_film_passes() -> None:
    # On a film of a hundred pages each beat is planned where its card falls, to the nearest page: all within 5%.
    assert check(100).problems(sheet(proportional(100)), scenes(*BEATS)) == ()


def test_a_beat_more_than_five_per_cent_of_the_film_out_of_place_is_named() -> None:
    starts = {**proportional(100), "All Is Lost": 85}
    found = check(100).problems(sheet(starts), scenes(*BEATS))
    assert found == (
        "All Is Lost begins 67% of the way through the script; the beat sheet puts it at 84%",
    )


def test_a_beat_with_no_scene_card_is_named() -> None:
    found = check(15).problems(sheet(), scenes(*(beat for beat in BEATS if beat != "Finale")))
    assert "Finale: no scene card is tagged with it" in found


def test_a_long_opening_scene_moves_every_beat_after_it() -> None:
    # The opening scene is thirty lines longer than the rest, so the Theme Stated card falls past the half-way mark.
    long_opening = scenes(BEATS[0], text=SCENE + "\n\n" + "\n\n".join(["More action."] * 30))
    found = check(15).problems(sheet(), long_opening + scenes(*BEATS[1:]))
    assert any(problem.startswith("Theme Stated begins") for problem in found)


def test_a_beat_the_sheet_does_not_plan_is_not_checked() -> None:
    # A row whose pages do not parse is left out of the plan, so its beat is not measured against it.
    rows = sheet({"All Is Lost": 14}).replace("All Is Lost | 14 to 14", "All Is Lost | x to y")
    assert check(15).problems(rows, scenes(*BEATS)) == ()


def test_a_card_tagged_with_a_name_outside_the_fifteen_is_not_named_here() -> None:
    # The scene still takes up its lines in the script, so the beats after it move; but the name itself is the
    # scene-cards check's to refuse, so this check never names it.
    found = check(15).problems(sheet(), scenes(*BEATS, "Interlude"))
    assert not any("Interlude" in problem for problem in found)


def test_a_film_with_no_pages_is_refused() -> None:
    with pytest.raises(ValueError, match="a film has a positive number of pages"):
        check(0)
