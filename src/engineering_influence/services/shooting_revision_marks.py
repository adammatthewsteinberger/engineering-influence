# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Marks a revised shooting script's changed scenes with their revision colour, against the baseline they came from."""

import re
from typing import ClassVar

from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)
from engineering_influence.services.interfaces.shooting_revision_marks_interface import (
    ShootingRevisionMarksInterface,
)


class ShootingRevisionMarks(ShootingRevisionMarksInterface):
    """Scenes are matched by their scene number, the label at the end of the heading, so a scene keeps its identity
    when others are added or cut. A scene is changed when it has no baseline scene with that number, or when its text
    differs from the baseline's, the number aside. Each changed scene gets a note above its heading, `[[revised:
    Blue *]]`, which the page layout reads as the revision colour and the mark in the margin.

    Revision 1 is Blue, 2 is Pink, and so on through the standard order; white is the baseline and has no revision.
    `BASELINE`, `REVISION` and `PAGES` are the artifact names the run keeps the baseline, the revision number and
    the marked script under.
    """

    BASELINE: ClassVar[str] = "previous_shooting_script.fountain"
    REVISION: ClassVar[str] = "revision.txt"
    PAGES: ClassVar[str] = "revision_pages.fountain"
    COLOURS: ClassVar[tuple[str, ...]] = (
        "White",
        "Blue",
        "Pink",
        "Yellow",
        "Green",
        "Goldenrod",
        "Buff",
        "Salmon",
        "Cherry",
        "Tan",
    )
    LABEL: ClassVar[re.Pattern[str]] = re.compile(r"\s#([^#\n]+)#\s*$")

    def __init__(self, parser: FountainParserInterface) -> None:
        self._parser = parser

    def mark(self, baseline: str, script: str, revision: int) -> str:
        """The script with its new or changed scenes noted; a scene without a number is refused, since it has no identity."""
        if not 1 <= revision < len(self.COLOURS):
            raise ValueError(f"a revision is numbered 1 to {len(self.COLOURS) - 1}, not {revision}")
        colour = self.COLOURS[revision]
        earlier = self._bodies(baseline)
        front, chunks = self._parser.scene_chunks(script)
        parts = [front.strip()] if front.strip() else []
        for chunk in chunks:
            label = self._label(chunk)
            if earlier.get(label) == self._body(chunk):
                parts.append(chunk.rstrip())
            else:
                parts.append(f"[[revised: {colour} *]]\n{chunk.rstrip()}")
        return "\n\n".join(parts) + "\n"

    def _bodies(self, baseline: str) -> dict[str, str]:
        _, chunks = self._parser.scene_chunks(baseline)
        return {self._label(chunk): self._body(chunk) for chunk in chunks}

    @classmethod
    def _label(cls, chunk: str) -> str:
        match = cls.LABEL.search(chunk.split("\n", 1)[0])
        if match is None:
            raise ValueError("a scene has no number, so it cannot be matched to the baseline")
        return match.group(1).strip()

    @classmethod
    def _body(cls, chunk: str) -> str:
        """The scene with its number removed from the heading: the text a revision is judged by."""
        heading, _, rest = chunk.rstrip().partition("\n")
        return f"{cls.LABEL.sub('', heading).rstrip()}\n{rest}"
