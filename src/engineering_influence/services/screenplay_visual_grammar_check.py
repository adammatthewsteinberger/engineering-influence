# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The visual grammar's mechanical checks: its two sections are present, the primary sets table has the four columns
and at least one set, and every major character has a visual signature."""

import re
from typing import ClassVar

from engineering_influence.services.interfaces.screenplay_visual_grammar_check_interface import (
    ScreenplayVisualGrammarCheckInterface,
)


class ScreenplayVisualGrammarCheck(ScreenplayVisualGrammarCheckInterface):
    """The primary sets are a table with the header `| Set | Light | Colour | Texture |` and at least one row whose four
    cells are all filled. Character signatures are bullets of the form `NAME: signature`, at least one of them. What the
    signatures look like stays with a reader."""

    SECTIONS: ClassVar[tuple[str, ...]] = ("Primary sets", "Character signatures")
    HEADER: ClassVar[tuple[str, ...]] = ("set", "light", "colour", "texture")
    HEADING: ClassVar[re.Pattern[str]] = re.compile(r"^## (.+?)\s*$", re.MULTILINE)

    def problems(self, text: str) -> tuple[str, ...]:
        """Every way the visual grammar breaks the format."""
        sections = self._sections(text)
        found = [
            f"the visual grammar needs a '## {name}' section"
            for name in self.SECTIONS
            if name not in sections
        ]
        if "Primary sets" in sections:
            found.extend(self._set_problems(sections["Primary sets"]))
        if "Character signatures" in sections:
            found.extend(self._signature_problems(sections["Character signatures"]))
        return tuple(found)

    @classmethod
    def _set_problems(cls, body: str) -> list[str]:
        rows = [
            tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
            for line in body.splitlines()
            if line.strip().startswith("|") and not set(line.strip()) <= set("|-: ")
        ]
        if not rows or tuple(cell.lower() for cell in rows[0]) != cls.HEADER:
            return ["the primary sets need a table headed '| Set | Light | Colour | Texture |'"]
        filled = [row for row in rows[1:] if len(row) == 4 and all(row)]
        if not filled:
            return [
                "the primary sets table has no set with its light, colour and texture filled in"
            ]
        return []

    @staticmethod
    def _signature_problems(body: str) -> list[str]:
        bullets = [line.strip()[2:] for line in body.splitlines() if line.strip().startswith("- ")]
        if not bullets:
            return ["the character signatures list no character"]
        return [
            f"signature {bullet!r} needs the form 'NAME: signature'"
            for bullet in bullets
            if not re.fullmatch(r".+?:\s*\S.*", bullet)
        ]

    @classmethod
    def _sections(cls, text: str) -> dict[str, str]:
        """Each section's name and the text under its heading, up to the next heading."""
        starts = list(cls.HEADING.finditer(text))
        sections: dict[str, str] = {}
        for position, match in enumerate(starts):
            end = starts[position + 1].start() if position + 1 < len(starts) else len(text)
            sections[match.group(1)] = text[match.end() : end]
        return sections
