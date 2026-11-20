# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The facts of a novel that every chapter has to agree with."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.story_bible_interface import StoryBibleInterface


@dataclass(frozen=True, slots=True)
class StoryBible(StoryBibleInterface):
    """The premise plus the names, places and dated events a continuity check compares against."""

    premise: str
    characters: tuple[str, ...] = ()
    places: tuple[str, ...] = ()
    timeline: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.premise.strip():
            raise ValueError("a story bible needs a premise")
        if len(set(self.characters)) != len(self.characters):
            raise ValueError("character names must be distinct")
