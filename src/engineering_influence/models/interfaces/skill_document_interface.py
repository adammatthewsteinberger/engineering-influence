# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SkillDocument."""

from abc import ABC, abstractmethod


class SkillDocumentInterface(ABC):
    """A skill as written in a SKILL.md file, cut into the sections a person can choose from."""

    __slots__ = ()

    @abstractmethod
    def titles(self) -> tuple[str, ...]:
        """The section titles, in the order they appear."""

    @abstractmethod
    def section(self, title: str) -> str | None:
        """The text of the section with this title, ignoring case, or None when there is none."""
