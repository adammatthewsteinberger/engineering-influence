# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One scene card of a screenplay: its number, its beat, and the card's text as the architecture stage wrote it."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.scene_card_interface import SceneCardInterface


@dataclass(frozen=True, slots=True)
class SceneCard(SceneCardInterface):
    """`number` runs from 1 in card order; `beat` names one of the fifteen beats; `body` is the card's text; `sources`
    are the numbers of the source files the scene draws on."""

    number: int
    beat: str
    body: str
    sources: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.number) is not int or self.number < 1:
            raise ValueError("a scene card is numbered from 1")
        if not self.beat.strip():
            raise ValueError("a scene card names its beat")
        if not self.sources or any(type(n) is not int or n < 1 for n in self.sources):
            raise ValueError("a scene card names at least one source, numbered from 1")

    def artifact(self) -> str:
        """The drafted scene's artifact name, `scenes/NNN.md`."""
        return f"scenes/{self.number:03d}.md"

    def revised(self) -> str:
        """The revised scene's artifact name, `revised/NNN.md`."""
        return f"revised/{self.number:03d}.md"

    def structured(self) -> str:
        """The scene after the structure pass, `structured/NNN.md`."""
        return f"structured/{self.number:03d}.md"

    def dialogued(self) -> str:
        """The scene after the dialogue pass, `dialogued/NNN.md`: the scene the assembly reads."""
        return f"dialogued/{self.number:03d}.md"
