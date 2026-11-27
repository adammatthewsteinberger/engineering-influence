# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayDialogueSourceCheck: a speech may not repeat twelve words of the sources in a row; action may."""

from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.screenplay_dialogue_source_check import (
    ScreenplayDialogueSourceCheck,
)

SOURCE = (
    "The reserve held forty days of air before the stack would crack under load and fail for good."
)
COPIED = "The reserve held forty days of air before the stack would crack"
COPIED_MESSAGE = 'dialogue repeats source text: "the reserve held forty days of ..."'


def check(scene: str, sources: str = SOURCE) -> tuple[str, ...]:
    return ScreenplayDialogueSourceCheck(FountainParser()).problems(scene, sources)


def speech(text: str) -> str:
    return f"INT. ROOM - DAY\n\nMARA\n{text}"


def test_a_speech_in_its_own_words_has_no_problems() -> None:
    assert (
        check(speech("We should check every valve in the reserve before the stack gets cold."))
        == ()
    )


def test_a_speech_that_repeats_twelve_words_of_the_source_is_a_problem() -> None:
    assert check(speech(f"{COPIED}, we know.")) == (COPIED_MESSAGE,)


def test_case_and_punctuation_do_not_hide_a_repeat() -> None:
    assert check(speech("THE RESERVE, held forty days of air! before the stack would crack.")) == (
        COPIED_MESSAGE,
    )


def test_eleven_shared_words_are_allowed() -> None:
    assert check(speech("The reserve held forty days of air before the stack would.")) == ()


def test_action_may_name_what_the_sources_say() -> None:
    scene = f"INT. ROOM - DAY\n\n{COPIED} under load."
    assert check(scene) == ()


def test_each_speech_that_repeats_the_source_is_its_own_problem() -> None:
    scene = f"INT. ROOM - DAY\n\nMARA\n{COPIED}.\n\nJON\n{COPIED}."
    assert check(scene) == (COPIED_MESSAGE, COPIED_MESSAGE)


def test_a_repeat_that_crosses_a_line_break_inside_one_speech_is_a_problem() -> None:
    scene = (
        "INT. ROOM - DAY\n\nMARA\nThe reserve held forty days\nof air before the stack would crack."
    )
    assert check(scene) == (COPIED_MESSAGE,)


def test_an_empty_source_has_nothing_to_repeat() -> None:
    assert check(speech(f"{COPIED}."), sources="") == ()
