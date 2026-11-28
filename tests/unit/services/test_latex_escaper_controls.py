# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Control characters are not printed: they are not TeX, but a stray one can fail a build or print oddly."""

from engineering_influence.services.typesetting.latex_escaper import LatexEscaper


def test_control_characters_are_removed_while_tabs_and_line_breaks_are_kept() -> None:
    assert LatexEscaper().escape("a\x07b\tc\nd\re\x7ff\x85g") == "ab\tc\ndefg"
