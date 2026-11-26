# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FountainAnswerScreen: a refusal is read from the action, never from a line of dialogue."""

from engineering_influence.services.fountain_answer_screen import FountainAnswerScreen
from engineering_influence.services.fountain_parser import FountainParser


def screen() -> FountainAnswerScreen:
    return FountainAnswerScreen(FountainParser())


def test_a_refusal_in_the_action_is_refused() -> None:
    assert screen().refused("INT. ROOM - DAY\n\nI can't write this scene.")


def test_a_character_saying_i_cant_is_not_a_refusal() -> None:
    assert not screen().refused("INT. ROOM - DAY\n\nMARA\nI can't do this anymore.")


def test_a_refusal_deep_in_the_action_is_not_read() -> None:
    filler = " ".join(["word"] * 200)
    assert not screen().refused(f"INT. ROOM - DAY\n\n{filler}\n\nI can't write this scene.")


def test_a_section_with_under_half_its_words_is_short() -> None:
    assert screen().short("one two three", 100)


def test_a_section_with_half_its_words_is_not_short() -> None:
    assert not screen().short(" ".join(["w"] * 10), 10)
