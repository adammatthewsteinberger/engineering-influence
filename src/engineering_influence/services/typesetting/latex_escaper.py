# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""LaTeX escaping of plain text."""

import re
from typing import ClassVar

from engineering_influence.services.typesetting.interfaces.latex_escaper_interface import (
    LatexEscaperInterface,
)


class LatexEscaper(LatexEscaperInterface):
    """Escapes LaTeX specials and applies light typographic fixes."""

    SPECIALS: ClassVar[dict[str, str]] = {
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
        "<": r"\textless{}",
        ">": r"\textgreater{}",
    }
    PATTERN = re.compile("|".join(re.escape(key) for key in SPECIALS))
    # Inside \\url{} a backslash or an unbalanced brace ends the argument and leaves the rest
    # as live TeX, so those three are percent-encoded, which is also how a URL spells them.
    URL_ENCODED: ClassVar[dict[str, str]] = {"\\": "%5C", "{": "%7B", "}": "%7D"}

    def escape(self, text: str) -> str:
        """Return text safe to place in a LaTeX body."""
        text = self.PATTERN.sub(lambda match: self.SPECIALS[match.group(0)], text)
        # A non-breaking space keeps "Chapter 7", "p. 12" and initials together.
        text = re.sub(r"\b(Chapters?|Psalms?|Part|pp?\.|No\.|vol\.) (\d)", r"\1~\2", text)
        return text.replace("...", r"\dots{}")

    def url(self, text: str) -> str:
        """Return a URL safe to place inside \\url{} or \\href{}: no live brace or backslash."""
        for char, code in self.URL_ENCODED.items():
            text = text.replace(char, code)
        return text.replace("%", r"\%").replace("#", r"\#")
