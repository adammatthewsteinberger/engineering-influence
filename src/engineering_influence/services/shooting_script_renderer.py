# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes the locked shooting script: each scene's number in its heading, and each omitted scene kept in its place."""

from typing import ClassVar

from engineering_influence.models.shooting_lock import ShootingLock
from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)
from engineering_influence.services.interfaces.shooting_script_renderer_interface import (
    ShootingScriptRendererInterface,
)


class ShootingScriptRenderer(ShootingScriptRendererInterface):
    """A numbered scene's heading gets its label at the end, as a Fountain scene number: `INT. ROOM - DAY #42A#`. An
    omitted scene becomes a forced heading, `.OMITTED #42#`, with nothing under it, so its number stays in the margin.
    The title page and the scenes' own text are kept as they are. Boneyard comments are removed, as the parser does.
    """

    OMITTED: ClassVar[str] = "OMITTED"

    def __init__(self, parser: FountainParserInterface) -> None:
        """Remember the Fountain parser the script is rendered with."""
        self._parser = parser

    def render(self, script: str, cards: tuple[int, ...], lock: ShootingLock) -> str:
        """The script with each scene given its locked number, and each omitted scene marked."""
        front, chunks = self._parser.scene_chunks(script)
        if len(chunks) != len(cards):
            raise ValueError("each scene card is one scene of the script")
        by_card = dict(zip(cards, chunks, strict=True))
        parts = [front.strip()] if front.strip() else []
        for entry in lock.entries:
            if entry.omitted:
                parts.append(f".{self.OMITTED} #{entry.label}#")
            else:
                parts.append(self._numbered(by_card[entry.card], entry.label))
        return "\n\n".join(parts) + "\n"

    @staticmethod
    def _numbered(chunk: str, label: str) -> str:
        """The scene's text with its label on the heading line."""
        heading, _, rest = chunk.partition("\n")
        return f"{heading.rstrip()} #{label}#\n{rest}".rstrip()
