# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A person in the story: the name the book uses, the other names for them, and their age."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.story_character_interface import (
    StoryCharacterInterface,
)
from engineering_influence.models.story_text import StoryText


@dataclass(frozen=True, slots=True)
class StoryCharacter(StoryCharacterInterface):
    """One character of the bible.

    ``age`` is the age at the story's opening, when the bible knows it; the bible's ``span_years`` says how much
    older the character may be written by the end. ``aliases`` are the other names the book may use (a nickname,
    a title) and are never flagged as a misspelling of the name.
    """

    MAX_NAME: ClassVar[int] = 80
    MAX_ALIASES: ClassVar[int] = 10
    MAX_AGE: ClassVar[int] = 150

    name: str
    aliases: tuple[str, ...] = ()
    age: int | None = None

    def __post_init__(self) -> None:
        """Validate the character's name, aliases and age when it is built."""
        StoryText.line("a character's name", self.name, self.MAX_NAME)
        if not isinstance(self.aliases, tuple) or len(self.aliases) > self.MAX_ALIASES:
            raise ValueError(f"a character has at most {self.MAX_ALIASES} aliases")
        for alias in self.aliases:
            StoryText.line("an alias", alias, self.MAX_NAME)
        folded = [form.casefold() for form in self.forms()]
        if len(set(folded)) != len(folded):
            raise ValueError("a character's name and aliases are each different")
        if self.age is not None and (
            type(self.age) is not int or not 0 <= self.age <= self.MAX_AGE
        ):
            raise ValueError(f"an age is a whole number from 0 to {self.MAX_AGE}")

    def forms(self) -> tuple[str, ...]:
        """Every way the book may write this character: the name, then the aliases."""
        return (self.name, *self.aliases)
