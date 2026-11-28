# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""LaTeX escaping of plain text."""

import re
from typing import ClassVar
from urllib.parse import quote

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
    # Control characters (C0 and C1, and DEL) other than tab and newline. They are not TeX, but a stray one can fail a
    # build or print oddly, so none reaches the page.
    CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
    PATTERN = re.compile("|".join(re.escape(key) for key in SPECIALS))
    # What may appear in a URL unencoded. Everything else, including backslash, braces, "^"
    # (TeX reads "^^5c" as a backslash inside any macro argument), quotes, "<", ">", spaces,
    # "$", control characters and every non-ASCII character, is percent-encoded, so the result
    # is a valid URI that can neither be TeX nor break out of an HTML attribute. "%" and "#"
    # are kept here and escaped for TeX below.
    URL_SAFE = "-._~:/?#[]@!&()*+,;=%"

    def escape(self, text: str) -> str:
        """Return text safe to place in a LaTeX body."""
        text = self.CONTROL.sub("", text)
        text = self.PATTERN.sub(lambda match: self.SPECIALS[match.group(0)], text)
        # A non-breaking space keeps "Chapter 7", "p. 12" and initials together.
        text = re.sub(r"\b(Chapters?|Psalms?|Part|pp?\.|No\.|vol\.) (\d)", r"\1~\2", text)
        return text.replace("...", r"\dots{}")

    def url(self, text: str) -> str:
        """Return a URL safe to place inside \\url{} or \\href{}: a valid URI, TeX-escaped."""
        encoded = quote(text, safe=self.URL_SAFE)
        return encoded.replace("%", r"\%").replace("#", r"\#")
