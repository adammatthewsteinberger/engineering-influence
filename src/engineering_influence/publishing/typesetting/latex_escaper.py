# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""LaTeX escaping of plain text."""

import re
from typing import ClassVar


class LatexEscaper:
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

    def escape(self, text: str) -> str:
        """Return text safe to place in a LaTeX body."""
        text = self.PATTERN.sub(lambda match: self.SPECIALS[match.group(0)], text)
        # A non-breaking space keeps "Chapter 7", "p. 12" and initials together.
        text = re.sub(r"\b(Chapters?|Psalms?|Part|pp?\.|No\.|vol\.) (\d)", r"\1~\2", text)
        return text.replace("...", r"\dots{}")
