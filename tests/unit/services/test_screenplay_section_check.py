# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplaySectionCheck: a drafted scene is one scene and follows the format rules that apply to a scene."""

from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.screenplay_section_check import ScreenplaySectionCheck


def check(section: str) -> tuple[str, ...]:
    return ScreenplaySectionCheck(FountainParser()).problems(section)


def test_a_good_scene_has_no_problems() -> None:
    assert check("INT. ROOM - DAY\n\nMara waits.\n\nMARA\nWe wait.") == ()


def test_a_section_with_no_scene_heading_is_a_problem() -> None:
    assert check("Mara waits.") == ("a section is one scene; it has 0 scene headings",)


def test_a_section_with_two_scenes_is_a_problem() -> None:
    assert check("INT. ROOM - DAY\n\nA.\n\nINT. HALL - DAY\n\nB.") == (
        "a section is one scene; it has 2 scene headings",
    )


def test_a_format_rule_applies_to_the_scene() -> None:
    problems = check("INT. ROOM - MORNING\n\nMara waits.")
    assert any("'MORNING' is not one of" in p for p in problems)
