"""Chapter openings: a drop cap followed by small caps."""

import re


class OpeningFormatter:
    """Every reader-facing chapter opening receives the large initial.

    A three-line drop cap needs enough text beside it. min_chars lets a book fall back to a
    plain small-caps opening for paragraphs shorter than that; the default never falls back.
    """

    def __init__(self, min_chars: int = 0) -> None:
        self._min_chars = min_chars

    def format(self, latex: str) -> str:
        """Set the first word of a chapter as a drop cap plus small caps."""
        match = re.match(r"([A-Z])([A-Za-z\u2019']*)(\s+)(.*)", latex, re.DOTALL)
        if not match:
            return r"\noindent " + latex
        first, rest_of_word, space, rest = match.groups()
        words = rest.split(" ")
        lead: list[str] = []
        while (
            words
            and len(lead) < 2
            and re.fullmatch(r"[A-Za-z\u2019',.;:]+", words[0])
            and not words[0].startswith("\\")
        ):
            lead.append(words.pop(0))
            if lead[-1][-1] in ",.;:":
                break
        lead_text = rest_of_word + (" " + " ".join(lead) if lead else "")
        plain = re.sub(r"\\[A-Za-z]+\*?|[{}]", "", latex)
        if len(plain) < self._min_chars:
            return r"\noindent{\capsfont " + first + lead_text + "}" + space + " ".join(words)
        return r"\opening{" + first + "}{" + lead_text + "}" + space + " ".join(words)
