# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""AnswerScreen: a refusal is a declining opening, and a short section is well under the length asked for."""

import pytest

from engineering_influence.services.answer_screen import AnswerScreen
from engineering_influence.services.interfaces.answer_screen_interface import (
    AnswerScreenInterface,
)


@pytest.mark.parametrize(
    "opening",
    [
        "I can't write that.",
        "I cannot help with this request.",
        "I won’t write it.",
        "I'm sorry, but I can't continue.",
        "I am unable to write that section.",
        "I'm not able to do that.",
        "I must decline.",
        "As an AI, I can't draft this.",
    ],
)
def test_a_declining_opening_is_a_refusal(opening: str) -> None:
    assert AnswerScreen().refused(opening + " " + "more words " * 40)


def test_prose_that_mentions_refusing_later_is_not_a_refusal() -> None:
    body = "Bees do not say no to the sun. " * 20 + "I can't stress enough how calm they are."
    assert not AnswerScreen().refused(body)


def test_a_refusal_past_the_opening_window_is_not_looked_for() -> None:
    text = "A calm opening about bees. " * 20 + "I can't write this."
    assert not AnswerScreen().refused(text)


def test_ordinary_prose_is_not_a_refusal() -> None:
    assert not AnswerScreen().refused("The hive wakes before dawn, and the first foragers leave.")


def test_a_section_under_half_its_length_is_short() -> None:
    screen = AnswerScreen()
    assert screen.short("word " * 1_249, 2_500)
    assert not screen.short("word " * 1_250, 2_500)


def test_it_is_an_answer_screen() -> None:
    assert isinstance(AnswerScreen(), AnswerScreenInterface)
