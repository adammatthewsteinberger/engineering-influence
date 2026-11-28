# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayLatexSource: a changed scene's heading gets a bar and a star in its revision colour; no other heading does."""

from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.screenplay_latex_source import ScreenplayLatexSource

MARKED = (
    "Title: TEST\n\nFADE IN:\n\n[[revised: Pink *]]\nINT. ROOM - DAY #1#\n\nAda waits.\n\n"
    "INT. HALL - DAY #2#\n\nA door opens.\n\nFADE OUT.\n\n>THE END<\n"
)


def render(script: str) -> str:
    return ScreenplayLatexSource(FountainParser()).render(script)


def test_the_marked_heading_gets_a_bar_and_star_in_its_colour() -> None:
    tex = render(MARKED)
    assert "\\llap{\\textcolor{revPink}{\\rule{3pt}{\\baselineskip}}" in tex
    assert tex.count("llap") == 1


def test_an_unmarked_heading_gets_no_bar() -> None:
    tex = render(MARKED)
    assert tex.index("llap") < tex.index("ROOM")
    assert "llap" not in tex[tex.index("HALL") :]


def test_every_revision_colour_is_defined_in_the_preamble() -> None:
    tex = render(MARKED)
    assert "\\usepackage{xcolor}" in tex
    for name in ("Blue", "Pink", "Tan"):
        assert f"\\definecolor{{rev{name}}}{{HTML}}" in tex


def test_a_script_with_no_marks_has_no_bars() -> None:
    assert "llap" not in render("FADE IN:\n\nINT. ROOM - DAY #1#\n\nAda waits.\n\nFADE OUT.\n")
