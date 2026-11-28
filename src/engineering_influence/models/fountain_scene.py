# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One scene of a Fountain screenplay: its heading, the notes on the heading, and its elements."""

from dataclasses import dataclass

from engineering_influence.models.fountain_block import FountainBlock
from engineering_influence.models.interfaces.fountain_scene_interface import FountainSceneInterface


@dataclass(frozen=True, slots=True)
class FountainScene(FountainSceneInterface):
    """`notes` are the (key, value) pairs of the heading's `[[key: value]]` notes, in order; a bare
    `[[value]]` is stored under the key `ref`."""

    number: int
    heading: str
    notes: tuple[tuple[str, str], ...]
    blocks: tuple[FountainBlock, ...]

    def __post_init__(self) -> None:
        """Validate the scene's heading notes when it is built."""
        if type(self.number) is not int or self.number < 1:
            raise ValueError("a scene is numbered from 1")
        if not self.heading.strip():
            raise ValueError("a scene has a heading")

    def text(self) -> str:
        """The heading and every element, one line each."""
        return "\n".join([self.heading, *(block.text() for block in self.blocks)])

    def note(self, key: str) -> str | None:
        """The value of the first note with this key, or None."""
        return next((value for name, value in self.notes if name == key), None)
