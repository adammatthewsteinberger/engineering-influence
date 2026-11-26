# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FountainPageEstimate: about how many Courier pages a script runs to, before it is rendered."""

from engineering_influence.services.fountain_page_estimate import FountainPageEstimate
from engineering_influence.services.fountain_parser import FountainParser


def estimate(text: str) -> float:
    return FountainPageEstimate(FountainParser()).pages(text)


def test_a_short_script_is_a_fraction_of_a_page() -> None:
    # transition 2 lines, heading 2, action 2: six lines over fifty-five a page.
    assert estimate("FADE IN:\n\nINT. ROOM - DAY\n\nMara waits.") == 0.1


def test_long_action_wraps_at_sixty_one_characters() -> None:
    body = " ".join(["ab"] * 120)  # twenty words of two letters fit in a line of sixty-one
    # transition 2, heading 2, six wrapped action lines plus its blank line: eleven lines.
    assert estimate(f"FADE IN:\n\nINT. ROOM - DAY\n\n{body}") == 0.2


def test_the_title_page_is_not_counted() -> None:
    body = "FADE IN:\n\nINT. ROOM - DAY\n\nMara waits."
    assert estimate(f"Title: LIVING WATERS\nAuthor: Adam\n\n{body}") == estimate(body)


def test_a_cue_counts_as_one_line() -> None:
    # transition 2, heading 2, cue 2, dialogue 2, closing transition 2, centred line 2: twelve lines.
    text = "FADE IN:\n\nINT. ROOM - DAY\n\nMARA\nWords.\n\nFADE OUT.\n\n>THE END<"
    assert estimate(text) == 0.2
