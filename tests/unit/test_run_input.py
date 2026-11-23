# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""RunInput: plain text a person gave a run, with a name, a size limit and no hidden characters."""

import hashlib

import pytest

from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.interfaces.run_input_interface import RunInputInterface
from engineering_influence.models.run_input import RunInput


def test_an_input_has_a_name_text_and_origin_and_a_digest_of_its_text() -> None:
    made = RunInput("notes", "Line one\n\tindented")
    assert isinstance(made, RunInputInterface)
    assert (made.name, made.origin) == ("notes", "pasted")
    assert made.digest() == hashlib.sha256(b"Line one\n\tindented").hexdigest()
    assert RunInput("notes", "é", "file").origin == "file"


@pytest.mark.parametrize(
    "name", ["", "Notes", "-notes", ".notes", "my notes", "n" * 61, "é", "a/b", 3]
)
def test_a_name_that_is_not_lowercase_and_safe_is_refused(name: object) -> None:
    with pytest.raises(ValueError, match="an input's name"):
        RunInput(name, "text")  # type: ignore[arg-type]


@pytest.mark.parametrize("name", ["a", "0", "notes.v2", "my_notes-1", "n" * 60])
def test_a_safe_name_is_accepted(name: str) -> None:
    assert RunInput(name, "text").name == name


def test_an_unknown_origin_is_refused() -> None:
    with pytest.raises(ValueError, match="comes from one of"):
        RunInput("notes", "text", "email")


@pytest.mark.parametrize("text", ["", "   \n\t", 3, None])
def test_blank_or_non_text_is_refused(text: object) -> None:
    with pytest.raises(ValueError, match="has text"):
        RunInput("notes", text)  # type: ignore[arg-type]


def test_the_most_characters_is_fifty_thousand_and_one_more_is_refused() -> None:
    assert len(RunInput("notes", "a" * 50_000).text) == 50_000
    with pytest.raises(ValueError, match="50,001 characters; the most is 50,000"):
        RunInput("notes", "a" * 50_001)


@pytest.mark.parametrize(
    "char",
    [
        "\x00",
        "\x1b",
        "\r",
        "\x7f",
        chr(0x200B),
        chr(0x202E),
        chr(0xFEFF),
        chr(0x2028),
        chr(0xE000),
        chr(0x3164),
        chr(0xFE0F),
        chr(0x0378),
    ],
)
def test_a_hidden_or_control_character_is_refused_and_named(char: str) -> None:
    with pytest.raises(ValueError, match=f"U\\+{ord(char):04X}"):
        RunInput("notes", f"safe {char} text")


def test_ordinary_unicode_text_is_fine() -> None:
    assert RunInput("notes", "Café — “quoted” 日本語 🙂").text.startswith("Café")


# ----------------------------------------------------------------------------- in a brief
def brief(*inputs: RunInput, **changes: object) -> BookBrief:
    return BookBrief(BookKind.NONFICTION, "an idea", 1_000_000, inputs=inputs, **changes)  # type: ignore[arg-type]


def test_a_brief_has_no_inputs_unless_given_some() -> None:
    assert BookBrief(BookKind.NONFICTION, "an idea", 1).inputs == ()
    assert brief(RunInput("a", "x"), RunInput("b", "y")).inputs[1].name == "b"


def test_a_brief_holds_eight_inputs_and_no_more() -> None:
    eight = tuple(RunInput(f"n{n}", "x") for n in range(8))
    assert len(brief(*eight).inputs) == 8
    with pytest.raises(ValueError, match="at most 8 inputs"):
        brief(*eight, RunInput("n8", "x"))


def test_a_brief_names_each_input_once() -> None:
    with pytest.raises(ValueError, match="names each input once"):
        brief(RunInput("a", "x"), RunInput("a", "y"))


def test_a_briefs_inputs_hold_two_hundred_thousand_characters_in_all() -> None:
    four = tuple(RunInput(f"n{n}", "a" * 50_000) for n in range(4))
    assert len(brief(*four).inputs) == 4
    with pytest.raises(ValueError, match="at most 200,000 characters in all"):
        brief(*four, RunInput("n4", "a"))


def test_a_brief_whose_inputs_are_not_a_tuple_of_inputs_is_refused() -> None:
    with pytest.raises(TypeError):
        BookBrief(BookKind.NONFICTION, "x", 1, inputs=[RunInput("a", "x")])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        BookBrief(BookKind.NONFICTION, "x", 1, inputs=("text",))  # type: ignore[arg-type]
