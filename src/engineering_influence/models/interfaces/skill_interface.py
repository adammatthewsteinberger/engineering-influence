# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Skill."""

from abc import ABC, abstractmethod


class SkillInterface(ABC):
    """A skill: text a person installed to steer a stage, and nothing a model can run."""

    __slots__ = ()

    @abstractmethod
    def identifier(self) -> str:
        """The name and version, as people write it: ``plain_style@2``."""

    @abstractmethod
    def stages(self) -> tuple[str, ...]:
        """The stages this skill has text for, in order."""

    @abstractmethod
    def part(self, stage: str) -> str | None:
        """The text for the stage, or None when the skill says nothing about it."""

    @abstractmethod
    def section_titles(self) -> tuple[str, ...]:
        """The titles of the reference sections a model may read on request, in order."""

    @abstractmethod
    def section(self, title: str) -> str | None:
        """The text of the reference section with exactly this title, or None."""
