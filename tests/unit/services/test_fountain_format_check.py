# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FountainFormatCheck: the mechanical format test of prompt 09, and the notes a reader should look at."""

from engineering_influence.services.fountain_format_check import FountainFormatCheck
from engineering_influence.services.fountain_parser import FountainParser


def checker(allowed_times: frozenset[str] | None = None) -> FountainFormatCheck:
    if allowed_times is None:
        return FountainFormatCheck(FountainParser())
    return FountainFormatCheck(FountainParser(), allowed_times)


def script(scene: str = "INT. ROOM - DAY", body: str = "Mara waits.", close: bool = True) -> str:
    ending = "FADE OUT.\n\n>THE END<" if close else "CUT TO BLACK."
    return f"FADE IN:\n\n{scene}\n\n{body}\n\n{ending}\n"


def speeches(count: int, parenthetical: int) -> str:
    lines = []
    for index in range(count):
        if index < parenthetical:
            lines.append("MARA\n(quietly)\nWe wait.\n")
        else:
            lines.append("MARA\nWe wait.\n")
    return "\n".join(lines)


def test_a_script_that_follows_the_format_has_no_problems() -> None:
    assert checker().problems(script()) == ()


def test_a_script_must_open_with_fade_in() -> None:
    text = script().replace("FADE IN:\n\n", "", 1)
    assert any("FADE IN:" in p for p in checker().problems(text))


def test_a_script_must_close_with_fade_out_and_the_end() -> None:
    assert any("FADE OUT. and then THE END" in p for p in checker().problems(script(close=False)))


def test_a_time_of_day_must_be_on_the_allowed_list() -> None:
    problems = checker().problems(script(scene="INT. ROOM - MORNING"))
    assert any("'MORNING' is not one of" in p for p in problems)


def test_a_heading_without_a_time_is_a_problem() -> None:
    assert any("has no time of day" in p for p in checker().problems(script(scene="INT. ROOM")))


def test_the_allowed_times_can_be_set_for_another_film() -> None:
    assert checker(frozenset({"MORNING"})).problems(script(scene="INT. ROOM - MORNING")) == ()


def test_a_year_in_a_heading_is_refused_in_favour_of_flashback() -> None:
    problems = checker().problems(script(scene="INT. ROOM (2028) - DAY"))
    assert any("use (FLASHBACK)" in p for p in problems)


def test_a_camera_direction_in_action_is_a_problem() -> None:
    assert any(
        "camera direction 'CLOSE ON'" in p
        for p in checker().problems(script(body="CLOSE ON her face."))
    )


def test_an_insert_is_allowed() -> None:
    assert checker().problems(script(body="INSERT: the letter.")) == ()


def test_digits_in_dialogue_are_a_problem() -> None:
    text = "FADE IN:\n\nINT. ROOM - DAY\n\nMARA\nI've known since 2025.\n\nFADE OUT.\n\n>THE END<"
    assert any("digits in dialogue" in p for p in checker().problems(text))


def test_a_parenthetical_must_lead_into_dialogue() -> None:
    text = "FADE IN:\n\nINT. ROOM - DAY\n\nMARA\n(quietly)\n\nFADE OUT.\n\n>THE END<"
    assert any("must lead into dialogue" in p for p in checker().problems(text))


def test_parentheticals_over_a_tenth_of_speeches_are_a_problem() -> None:
    text = f"FADE IN:\n\nINT. ROOM - DAY\n\n{speeches(10, 2)}\nFADE OUT.\n\n>THE END<"
    assert any("parentheticals on 10 speeches" in p for p in checker().problems(text))


def test_a_tenth_of_speeches_is_within_the_limit() -> None:
    text = f"FADE IN:\n\nINT. ROOM - DAY\n\n{speeches(10, 1)}\nFADE OUT.\n\n>THE END<"
    assert checker().problems(text) == ()


def test_the_ratio_is_not_judged_on_a_short_script() -> None:
    text = f"FADE IN:\n\nINT. ROOM - DAY\n\n{speeches(3, 3)}\nFADE OUT.\n\n>THE END<"
    assert checker().problems(text) == ()


def test_interior_thought_in_action_is_a_note_not_a_problem() -> None:
    text = script(body="Mara knows the truth.")
    assert checker().problems(text) == ()
    assert any("interior thought in action" in note for note in checker().notes(text))
