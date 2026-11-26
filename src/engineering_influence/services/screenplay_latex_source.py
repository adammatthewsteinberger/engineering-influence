# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Lays out a Fountain script as the LaTeX of standard screenplay pages: US Letter, Courier, and the element indents."""

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
        """The whole document: the preamble, the title page, then the body."""
        title = self._title_page(script)
        body = "\n".join(self._element(kind, lines) for kind, lines in self._elements(script))
        return f"{self._preamble()}\n\\begin{{document}}\n{title}\n{body}\n\\end{{document}}\n"

    def _elements(self, script: str) -> list[tuple[str, tuple[str, ...]]]:
        return [(block.kind, block.lines) for block in self._parser.blocks(script)]

    def _element(self, kind: str, lines: tuple[str, ...]) -> str:
        text = " \\\\\n".join(self._escape(line) for line in lines)
        if kind == "heading":
            text = text.upper()
            return f"\\par\\noindent{{\\bfseries {text}}}\\par"
        if kind == "transition":
            return f"\\par{{\\raggedleft {text}\\par}}"
        if kind == "centered":
            return f"\\par{{\\centering {text}\\par}}"
        left, right = self.INDENTS[kind]
        return f"\\par{{\\leftskip={left}in \\rightskip={right}in \\noindent {text}\\par}}"

    def _title_page(self, script: str) -> str:
        pairs = self._parser.title_page(script)
        lines = "\n".join(
            f"\\par{{\\centering\\bfseries {self._escape(key)}: {self._escape(value)}\\par}}"
            for key, value in pairs
        )
        return f"\\vspace*{{3in}}\n{lines}\n\\clearpage"

    def _preamble(self) -> str:
        return "\n".join(
            (
                "\\documentclass[12pt]{article}",
                "\\usepackage{fontspec}",
                "\\usepackage[paperwidth=8.5in,paperheight=11in,left=1.5in,right=1in,top=1in,bottom=1in]{geometry}",
                f"\\setmainfont{{{self.FONT}}}",
                "\\setlength{\\parindent}{0pt}",
                "\\setlength{\\parskip}{12pt}",
                "\\setlength{\\baselineskip}{12pt}",
                "\\pagestyle{empty}",
            )
        )

    def _escape(self, text: str) -> str:
        return "".join(self.ESCAPES.get(character, character) for character in text)
