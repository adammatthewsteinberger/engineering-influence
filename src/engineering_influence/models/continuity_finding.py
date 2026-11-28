# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One place where a chapter disagrees with the story bible."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.continuity_finding_interface import (
    ContinuityFindingInterface,
)
from engineering_influence.models.story_text import StoryText


@dataclass(frozen=True, slots=True)
class ContinuityFinding(ContinuityFindingInterface):
    """A chapter, what kind of disagreement, the bible's word for it, what the chapter wrote and a plain sentence.

    ``kind`` is one of ``KINDS``: ``name`` and ``place`` for a spelling that is one letter from a known one,
    ``age`` for an age outside what the bible allows, ``timeline`` for events mentioned out of their order.
    A finding is a question for the author or the next stage, not a verdict: a flashback is a legitimate
    reason for an event out of order.
    """

    KINDS: ClassVar[tuple[str, ...]] = ("name", "place", "age", "timeline")
    MAX_TEXT: ClassVar[int] = 300

    chapter: int
    kind: str
    expected: str
    found: str
    message: str

    def __post_init__(self) -> None:
        """Validate the finding's fields when it is built."""
        if type(self.chapter) is not int or self.chapter < 1:
            raise ValueError("a finding names a chapter from 1")
        if self.kind not in self.KINDS:
            raise ValueError(f"a finding's kind is one of {', '.join(self.KINDS)}")
        StoryText.line("what the bible has", self.expected, self.MAX_TEXT)
        StoryText.line("what the chapter wrote", self.found, self.MAX_TEXT)
        StoryText.line("a finding's message", self.message, self.MAX_TEXT)

    def render(self) -> str:
        """The finding as one line a person can act on: ``chapter 3 (name): ...``."""
        return f"chapter {self.chapter} ({self.kind}): {self.message}"
