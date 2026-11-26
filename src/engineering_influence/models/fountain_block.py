# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One element of a Fountain screenplay: a heading, an action paragraph, a cue, dialogue and so on."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.fountain_block_interface import FountainBlockInterface


@dataclass(frozen=True, slots=True)
class FountainBlock(FountainBlockInterface):
    """The kind of element and its lines, with notes already taken out.

    A dialogue block holds the consecutive dialogue lines of one speech; a parenthetical block holds the
    consecutive parenthetical lines between a cue and its dialogue.
    """

    KINDS: ClassVar[frozenset[str]] = frozenset(
        {"heading", "action", "cue", "parenthetical", "dialogue", "transition", "centered"}
    )

    kind: str
    lines: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.kind not in self.KINDS:
            raise ValueError(f"a Fountain block is one of {sorted(self.KINDS)}, not {self.kind!r}")
        if not self.lines:
            raise ValueError("a Fountain block has at least one line")

    def text(self) -> str:
        """The lines joined with newlines."""
        return "\n".join(self.lines)
