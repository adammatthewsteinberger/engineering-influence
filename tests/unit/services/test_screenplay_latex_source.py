# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayLatexSource: standard screenplay layout in LaTeX, with LaTeX's own characters escaped."""

from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.screenplay_latex_source import ScreenplayLatexSource


def render(script: str) -> str:
    return ScreenplayLatexSource(FountainParser()).render(script)


def test_the_document_has_the_standard_page_and_font() -> None:
    tex = render("Title: TEST FILM\n\nFADE IN:\n")
    assert "\\documentclass[12pt]{article}" in tex
    assert "paperwidth=8.5in" in tex and "left=1.5in" in tex
    assert "\\setmainfont{TeX Gyre Cursor}" in tex
    assert tex.index("\\begin{document}") < tex.index("\\end{document}")


def test_the_title_page_is_centred_and_ends_its_page() -> None:
    tex = render("Title: TEST FILM\nCredit: Written by\n\nFADE IN:\n")
    assert "\\centering\\bfseries Title: TEST FILM" in tex
    assert "\\centering\\bfseries Credit: Written by" in tex
    assert "\\clearpage" in tex


def test_a_scene_heading_is_capitalised_and_bold() -> None:
    assert "{\\bfseries INT. HIVE - DAY}" in render("Title: T\n\nINT. hive - day\n")


def test_dialogue_is_indented_under_its_cue() -> None:
    tex = render("Title: T\n\nJOHN\nIs she gone?\n")
    assert "\\leftskip=2.2in" in tex
    assert "\\leftskip=1.0in \\rightskip=1.5in \\noindent Is she gone?" in tex


def test_a_parenthetical_has_its_own_narrower_indent() -> None:
    tex = render("Title: T\n\nJOHN\n(quietly)\nHello.\n")
    assert "\\leftskip=1.6in \\rightskip=2.9in \\noindent (quietly)" in tex


def test_a_transition_is_flush_right_and_a_centred_line_is_centred() -> None:
    tex = render("Title: T\n\nCUT TO:\n\n> THE END <\n")
    assert "\\raggedleft CUT TO:" in tex
    assert "\\centering THE END" in tex


def test_dialogue_lines_of_one_speech_break_on_their_own_lines() -> None:
    tex = render("Title: T\n\nJOHN\nFirst line.\nSecond line.\n")
    assert "First line. \\\\\nSecond line." in tex


def test_characters_that_mean_something_to_latex_are_escaped() -> None:
    tex = render("Title: T\n\nAction costs $5 & 50% of {x} #1 ~ a_b ^ c \\ d.\n")
    assert "\\$5 \\& 50\\% of \\{x\\} \\#1" in tex
    assert "\\textasciitilde{}" in tex and "a\\_b" in tex
    assert "\\textasciicircum{}" in tex and "\\textbackslash{}" in tex


def test_the_title_value_is_escaped_too() -> None:
    assert "Fish \\& Chips" in render("Title: Fish & Chips\n\nFADE IN:\n")
