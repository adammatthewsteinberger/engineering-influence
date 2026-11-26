# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""NarrationText: markdown is taken out, sentences stay whole, and no segment is longer than the limit."""

from engineering_influence.services.interfaces.narration_text_interface import (
    NarrationTextInterface,
)
from engineering_influence.services.narration_text import NarrationText


def test_markdown_is_taken_out_and_the_words_kept() -> None:
    text = "## Chapter 2: Water\n\nDrink **plenty** of _water_, see [the guide](http://x) and `code`.[^3]"
    assert NarrationText().segments(text) == (
        "Chapter 2: Water",
        "Drink plenty of water, see the guide and code.",
    )


def test_paragraphs_stay_in_order_and_empty_ones_are_dropped() -> None:
    assert NarrationText().segments("One.\n\n\n\nTwo.\n\n   \n\nThree.") == (
        "One.",
        "Two.",
        "Three.",
    )


def test_a_long_chapter_is_cut_at_sentences_and_no_segment_is_too_long() -> None:
    sentence = "Bees keep their hive warm all winter. "
    segments = NarrationText().segments(sentence * 60)
    assert len(segments) > 1
    assert all(len(segment) <= NarrationText.MAX_CHARACTERS for segment in segments)
    assert all(segment.endswith(".") for segment in segments)


def test_a_sentence_longer_than_the_limit_is_cut_at_a_space_and_no_word_is_split() -> None:
    word_run = " ".join(["honeycomb"] * 200)
    segments = NarrationText().segments(word_run)
    assert all(len(segment) <= NarrationText.MAX_CHARACTERS for segment in segments)
    assert " ".join(segments).split() == word_run.split()


def test_a_chapter_with_no_words_gives_no_segments() -> None:
    assert NarrationText().segments("[^1]\n\n***") == ()


def test_it_is_a_narration_text() -> None:
    assert isinstance(NarrationText(), NarrationTextInterface)


def test_a_word_longer_than_the_limit_with_no_space_is_cut_at_the_limit() -> None:
    segments = NarrationText().segments("x" * (NarrationText.MAX_CHARACTERS * 2 + 5))
    assert [len(segment) for segment in segments] == [
        NarrationText.MAX_CHARACTERS,
        NarrationText.MAX_CHARACTERS,
        5,
    ]
