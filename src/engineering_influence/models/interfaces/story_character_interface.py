# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for StoryCharacter."""

from abc import ABC, abstractmethod


class StoryCharacterInterface(ABC):
    """A person in the story: the name the book uses, the other names for them, and their age."""

    __slots__ = ()

    @abstractmethod
    def forms(self) -> tuple[str, ...]:
        """Every way the book may write this character: the name, then the aliases."""
