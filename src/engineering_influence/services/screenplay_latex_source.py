# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Lays out a Fountain script as the LaTeX of standard screenplay pages: US Letter, Courier, and the element indents."""

import re
from typing import ClassVar

from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)
from engineering_influence.services.interfaces.screenplay_latex_source_interface import (
    ScreenplayLatexSourceInterface,
)


class ScreenplayLatexSource(ScreenplayLatexSourceInterface):
    """Standard screenplay layout: a 1.5 inch left margin, 1 inch elsewhere, 12 point Courier on a 12 point line.

    Each element is indented from the left margin by the same amounts a studio template uses: a character name 2.2
    inches, dialogue 1.0 inch (3.5 inches wide), a parenthetical 1.6 inches (2.0 wide), a transition flush right.
    Every element is one paragraph group, so its indent and width are set for that group alone. Characters that mean
    something to LaTeX are escaped, so a line of text prints as it was written.
    """

    FONT: ClassVar[str] = "TeX Gyre Cursor"
    # The revision colours, as RGB hex. Approximations of the studio colours: a revision's bar and mark print in one.
    REVISION_HEX: ClassVar[dict[str, str]] = {
        "Blue": "2E75B6",
        "Pink": "E83E8C",
        "Yellow": "F2C94C",
        "Green": "3DAA5B",
        "Goldenrod": "DAA520",
        "Buff": "E9D8A6",
        "Salmon": "F08A6A",
        "Cherry": "B0243C",
        "Tan": "C8A27C",
    }
    # A revision note, as the revision marks write it above a changed scene's heading.
    REVISION_NOTE: ClassVar[re.Pattern[str]] = re.compile(r"^\[\[revised: (\w+) \*\]\]$")
    ESCAPES: ClassVar[dict[str, str]] = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "&": r"\&",
        "#": r"\#",
        "%": r"\%",
        "_": r"\_",
        "^": r"\textasciicircum{}",
        "~": r"\textasciitilde{}",
    }
    # (left indent, right indent) from the margin, in inches: the text width is 6.0 inches.
    INDENTS: ClassVar[dict[str, tuple[float, float]]] = {
        "action": (0.0, 0.0),
        "cue": (2.2, 0.0),
        "dialogue": (1.0, 1.5),
        "parenthetical": (1.6, 2.9),
    }

    def __init__(self, parser: FountainParserInterface) -> None:
        self._parser = parser

    def render(self, script: str) -> str:
        """The whole document: the preamble, the title page, then the body. A changed scene's heading is marked in its
        revision colour, with a bar and a star in the margin."""
        header = self._header(script)
        title = self._title_page(script, header is not None)
        revisions = self._revisions(script)
        body = "\n".join(
            self._element(kind, lines, revisions) for kind, lines in self._elements(script)
        )
        return (
            f"{self._preamble(header)}\n\\begin{{document}}\n{title}\n{body}\n\\end{{document}}\n"
        )

    def _header(self, script: str) -> str | None:
        """The running header of a revision script: its title page's Revision line, escaped. An ordinary script has none."""
        for key, value in self._parser.title_page(script):
            if key == "Revision":
                return self._escape(f"{key}: {value}")
        return None

    def _elements(self, script: str) -> list[tuple[str, tuple[str, ...]]]:
        return [(block.kind, block.lines) for block in self._parser.blocks(script)]

    def _revisions(self, script: str) -> dict[str, str]:
        """Each marked scene's heading line, with its revision colour, from the note written just above it."""
        marked: dict[str, str] = {}
        pending: str | None = None
        for line in script.splitlines():
            note = self.REVISION_NOTE.match(line.strip())
            if note is not None:
                pending = note.group(1)
            elif pending is not None and line.strip():
                marked[line.strip()] = pending
                pending = None
        return marked

    def _element(
        self, kind: str, lines: tuple[str, ...], revisions: dict[str, str] | None = None
    ) -> str:
        if kind == "heading":
            colour = (revisions or {}).get(lines[0]) if lines else None
            return self._heading(lines, colour)
        text = " \\\\\n".join(self._escape(line) for line in lines)
        if kind == "transition":
            return f"\\par{{\\raggedleft {text}\\par}}"
        if kind == "centered":
            return f"\\par{{\\centering {text}\\par}}"
        left, right = self.INDENTS[kind]
        return f"\\par{{\\leftskip={left}in \\rightskip={right}in \\noindent {text}\\par}}"

    def _heading(self, lines: tuple[str, ...], colour: str | None = None) -> str:
        """The heading in bold capitals, with its locked scene number at the right margin when it has one. A changed
        scene's heading has a bar and a star in the left margin, in its revision colour."""
        plain, number = self._parser.split_scene_number(" ".join(lines))
        text = self._escape(plain.upper())
        mark = "" if colour is None else self._margin_mark(colour)
        if number is None:
            return f"\\par\\noindent{mark}{{\\bfseries {text}}}\\par"
        return f"\\par\\noindent{mark}{{\\bfseries {text}\\hfill {self._escape(number)}}}\\par"

    @staticmethod
    def _margin_mark(colour: str) -> str:
        """A bar and a star, set in the left margin in the revision colour."""
        return (
            f"\\llap{{\\textcolor{{rev{colour}}}{{\\rule{{3pt}}{{\\baselineskip}}}}\\hspace{{5pt}}"
            f"\\textcolor{{rev{colour}}}{{*}}\\hspace{{4pt}}}}"
        )

    def _title_page(self, script: str, headed: bool = False) -> str:
        pairs = self._parser.title_page(script)
        lines = "\n".join(
            f"\\par{{\\centering\\bfseries {self._escape(key)}: {self._escape(value)}\\par}}"
            for key, value in pairs
        )
        # The title page of a revision script is the only page without its running header.
        unheaded = "\\thispagestyle{empty}\n" if headed else ""
        return f"{unheaded}\\vspace*{{3in}}\n{lines}\n\\clearpage"

    def _preamble(self, header: str | None = None) -> str:
        page_style: tuple[str, ...] = (
            ("\\pagestyle{empty}",)
            if header is None
            else (
                "\\usepackage{fancyhdr}",
                "\\pagestyle{fancy}",
                "\\fancyhf{}",
                f"\\fancyhead[R]{{\\small {header}}}",
                "\\renewcommand{\\headrulewidth}{0pt}",
            )
        )
        return "\n".join(
            (
                "\\documentclass[12pt]{article}",
                "\\usepackage{fontspec}",
                "\\usepackage{xcolor}",
                *(
                    f"\\definecolor{{rev{name}}}{{HTML}}{{{hex_value}}}"
                    for name, hex_value in self.REVISION_HEX.items()
                ),
                "\\usepackage[paperwidth=8.5in,paperheight=11in,left=1.5in,right=1in,top=1in,bottom=1in]{geometry}",
                f"\\setmainfont{{{self.FONT}}}",
                "\\setlength{\\parindent}{0pt}",
                "\\setlength{\\parskip}{12pt}",
                "\\setlength{\\baselineskip}{12pt}",
                *page_style,
            )
        )

    def _escape(self, text: str) -> str:
        return "".join(self.ESCAPES.get(character, character) for character in text)
