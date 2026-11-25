# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What the outline says about one chapter: its title, purpose, beats and the claims it will need sources for."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.chapter_outline_interface import (
    ChapterOutlineInterface,
)


@dataclass(frozen=True, slots=True)
class ChapterOutline(ChapterOutlineInterface):
    """One chapter of the plan, as plain one-line texts.

    Everything here came out of a model, so it is only ever put in a later prompt inside an
    ``<untrusted>`` block. It is held to what can be shown on one line: no line breaks, no control
    characters, a length limit on each text, and at most ``MAX_BEATS`` beats and ``MAX_CLAIMS``
    claims, so one chapter cannot make a later prompt unbounded.
    """

    MAX_TITLE: ClassVar[int] = 160
    MAX_TEXT: ClassVar[int] = 600
    MAX_BEATS: ClassVar[int] = 10
    MAX_CLAIMS: ClassVar[int] = 20

    number: int
    title: str
    purpose: str
    beats: tuple[str, ...]
    claims: tuple[str, ...] = ()
    leads_to: str = ""

    def __post_init__(self) -> None:
        if type(self.number) is not int or self.number < 1:
            raise ValueError("a chapter number is a whole number from 1")
        self._line("the title", self.title, self.MAX_TITLE)
        self._line("the purpose", self.purpose, self.MAX_TEXT)
        if not isinstance(self.beats, tuple) or not self.beats:
            raise ValueError("a chapter needs at least one beat")
        if len(self.beats) > self.MAX_BEATS:
            raise ValueError(f"a chapter has at most {self.MAX_BEATS} beats")
        for beat in self.beats:
            self._line("a beat", beat, self.MAX_TEXT)
        if not isinstance(self.claims, tuple) or len(self.claims) > self.MAX_CLAIMS:
            raise ValueError(f"a chapter lists at most {self.MAX_CLAIMS} claims to source")
        for claim in self.claims:
            self._line("a claim", claim, self.MAX_TEXT)
        if self.leads_to:
            self._line("what it leads to", self.leads_to, self.MAX_TEXT)

    def heading(self) -> str:
        """The chapter as people name it: ``Chapter 3: The Hive``."""
        return f"Chapter {self.number}: {self.title}"

    def render(self) -> str:
        """The chapter as the lines a drafting prompt shows: heading, purpose, beats, claims, where it leads."""
        lines = [self.heading(), f"Purpose: {self.purpose}", "Beats:"]
        lines += [f"- {beat}" for beat in self.beats]
        if self.claims:
            lines += ["Claims to source:", *(f"- {claim}" for claim in self.claims)]
        if self.leads_to:
            lines.append(f"Leads to: {self.leads_to}")
        return "\n".join(lines)

    @staticmethod
    def _line(label: str, text: str, limit: int) -> None:
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{label} needs text")
        if len(text) > limit:
            raise ValueError(f"{label} is longer than {limit} characters")
        if text != text.strip() or not text.isprintable():
            raise ValueError(f"{label} is one line of printable text")
