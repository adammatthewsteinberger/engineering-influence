# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ChapterCleaner: dashes are rewritten, unfinished work is refused, the heading is the outline's."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.services.chapter_cleaner import ChapterCleaner
from engineering_influence.services.interfaces.chapter_cleaner_interface import (
    ChapterCleanerInterface,
)

EM = chr(0x2014)
EN = chr(0x2013)
CLEANER = ChapterCleaner()


def clean(text: str, number: int = 2, title: str = "The Site") -> str:
    return CLEANER.clean(number, title, text)


def refused(text: str) -> str:
    with pytest.raises(ApplicationError) as error:
        clean(text)
    assert (error.value.code, error.value.http_status) == ("MANUSCRIPT_TEXT_REFUSED", 422)
    return error.value.message


def test_it_is_a_chapter_cleaner() -> None:
    assert isinstance(CLEANER, ChapterCleanerInterface)


def test_the_chapter_is_the_outlines_title_then_the_body_and_ends_with_a_newline() -> None:
    assert clean("First paragraph.\n\nSecond.") == "# The Site\n\nFirst paragraph.\n\nSecond.\n"


@pytest.mark.parametrize(
    "heading",
    [
        "Chapter 2: The Site",
        "## Chapter 2: The Site",
        "# The Site",
        "### Anything at all",
        "  Chapter 2. Site",
    ],
)
def test_a_heading_the_model_put_at_the_top_is_dropped_for_the_outlines_title(heading: str) -> None:
    assert clean(f"\n\n{heading}\n\nBody text.") == "# The Site\n\nBody text.\n"


def test_text_right_under_the_heading_with_no_blank_line_is_kept() -> None:
    assert clean("Chapter 2: The Site\nStraight into it.") == "# The Site\n\nStraight into it.\n"


def test_a_first_line_that_is_not_a_heading_is_kept() -> None:
    assert clean("Chapters begin with a story.\n\nMore.") == (
        "# The Site\n\nChapters begin with a story.\n\nMore.\n"
    )


def test_only_the_first_heading_is_dropped() -> None:
    assert clean("# One\n\n## Two\n\nBody.") == "# The Site\n\n## Two\n\nBody.\n"


def test_another_level_one_heading_in_the_body_becomes_level_two() -> None:
    assert clean("Intro.\n\n# Extra\n\nText.") == "# The Site\n\nIntro.\n\n## Extra\n\nText.\n"


def test_a_hash_line_inside_a_fenced_block_is_left_alone() -> None:
    text = "Intro.\n\n```\n# a shell comment\n```\n\n~~~\n# also\n~~~\n\n# Real"
    assert clean(text) == (
        "# The Site\n\nIntro.\n\n```\n# a shell comment\n```\n\n~~~\n# also\n~~~\n\n## Real\n"
    )


def test_windows_line_endings_are_made_plain() -> None:
    assert clean("# T\r\n\r\nOne.\r\nTwo.\r") == "# The Site\n\nOne.\nTwo.\n"


@pytest.mark.parametrize(
    ("written", "cleaned"),
    [
        (f"slow {EM} and steady", "slow, and steady"),
        (f"slow{EM}and steady", "slow, and steady"),
        (f"slow {EN} and steady", "slow, and steady"),
        (f"in 1990{EN}1995 it rose", "in 1990-1995 it rose"),
        (f"{EM} said the bee", "said the bee"),
        (f"he stopped {EM}\nthen went on", "he stopped\nthen went on"),
        (f"a pause {EM}. Then", "a pause. Then"),
        (f"(an aside {EM})", "(an aside)"),
        (f"three {EM}{EM} four", "three, , four"),
        ("a comma, and another,\nthen more", "a comma, and another,\nthen more"),
    ],
)
def test_dashes_are_rewritten_and_ordinary_commas_are_kept(written: str, cleaned: str) -> None:
    assert clean(f"# T\n\n{written}") == f"# The Site\n\n{cleaned}\n"


@pytest.mark.parametrize(
    ("marker", "matched"),
    [
        ("[TODO]", "[TODO"),
        ("[TBD: fill in", "[TBD"),
        ("[VERIFY", "[VERIFY"),
        ("[INSERT image]", "[INSERT"),
        ("[LIKELY", "[LIKELY"),
        ("[CALLOUT", "[CALLOUT"),
        ("[/CALLOUT]", "[/CALLOUT"),
        ("[TESTIMONY", "[TESTIMONY"),
        ("[PLACEHOLDER]", "[PLACEHOLDER"),
        ("[ILLUSTRATION", "[ILLUSTRATION"),
    ],
)
def test_an_unfinished_marker_is_refused_with_the_chapter_and_the_line(
    marker: str, matched: str
) -> None:
    assert refused(f"# T\n\nOne.\n\nTwo {marker} here.") == (
        f"chapter 2, line 5: an unfinished marker ({matched!r}); the book cannot be typeset with it"
    )


def test_the_word_draft_is_refused_but_longer_words_and_lower_case_are_not() -> None:
    assert refused("One.\nA Draft of it.") == (
        "chapter 2, line 2: the word 'Draft' ('Draft'); the book cannot be typeset with it"
    )
    assert clean("Drafting a draft with Drafts.") == "# The Site\n\nDrafting a draft with Drafts.\n"


def test_the_line_counts_the_model_text_not_the_cleaned_text() -> None:
    assert "line 4:" in refused("Chapter 2: Site\n\nOne.\n[TODO]")


def test_a_chapter_with_nothing_after_its_heading_is_refused() -> None:
    assert refused("Chapter 2: The Site\n\n  \n") == "chapter 2 has no text after its heading"
    assert refused("") == "chapter 2 has no text after its heading"


@given(st.text())
def test_whatever_the_model_wrote_is_refused_or_has_no_dash_marker_or_draft_left(text: str) -> None:
    try:
        cleaned = clean(text)
    except ApplicationError:
        return
    assert EM not in cleaned and EN not in cleaned
    assert "Draft" not in cleaned and "[TODO" not in cleaned
    assert cleaned.startswith("# The Site\n\n") and cleaned.endswith("\n")
