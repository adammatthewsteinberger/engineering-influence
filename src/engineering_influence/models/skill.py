# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A skill: text a person installed to steer a stage, and nothing a model can run."""

import re
import unicodedata
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.skill_interface import SkillInterface


@dataclass(frozen=True, slots=True)
class Skill(SkillInterface):
    """A versioned prompt pack: one piece of text for each stage it speaks to.

    A skill is data. It has no command, no tool, no address and no blanks to fill, so loading one
    cannot run anything, reach anything or widen what a stage may call (ADR 0008, decision 8). Its
    text reaches a model only when a person has enabled the skill for a stage, and then only inside
    a block the product delimits and labels.

    The text a person approved is exactly the text a model sees, so the text is held to what a
    person can read: no control characters, and none of the characters that render as nothing or
    reorder what is shown (zero-width and bidirectional marks, line and paragraph separators,
    private-use and unassigned code points). Those are the usual way to hide an instruction in
    text that looks harmless in review. A part is also capped, because a skill is added to a
    prompt that already has a budget.
    """

    NAME: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]*")
    MAX_PARTS: ClassVar[int] = 32
    MAX_PART_CHARS: ClassVar[int] = 8_000
    MAX_DESCRIPTION_CHARS: ClassVar[int] = 300
    HIDDEN: ClassVar[frozenset[str]] = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"})

    name: str
    version: int
    parts: tuple[tuple[str, str], ...]
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.NAME.fullmatch(self.name):
            raise ValueError("a skill name is lowercase letters, digits and underscores")
        if type(self.version) is not int or self.version < 1:
            raise ValueError("a skill version is a whole number from 1")
        if not isinstance(self.description, str) or len(self.description) > (
            self.MAX_DESCRIPTION_CHARS
        ):
            raise ValueError(
                f"a description is text of at most {self.MAX_DESCRIPTION_CHARS} characters"
            )
        if "\n" in self.description:
            raise ValueError("a description is one line")
        self._plain("the description", self.description)
        if not isinstance(self.parts, tuple) or not self.parts:
            raise ValueError("a skill needs at least one part")
        if len(self.parts) > self.MAX_PARTS:
            raise ValueError(f"a skill has at most {self.MAX_PARTS} parts")
        for part in self.parts:
            if not isinstance(part, tuple) or len(part) != 2:
                raise TypeError("a part is a (stage, text) pair")
        stages = [stage for stage, _ in self.parts]
        if any(not isinstance(stage, str) or not self.NAME.fullmatch(stage) for stage in stages):
            raise ValueError("a part is named for a stage: lowercase letters, digits, underscores")
        if stages != sorted(set(stages)):
            raise ValueError("a skill has one part for each stage, in stage order")
        for stage, text in self.parts:
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"the part for {stage!r} needs text")
            if len(text) > self.MAX_PART_CHARS:
                raise ValueError(
                    f"the part for {stage!r} is longer than {self.MAX_PART_CHARS} characters"
                )
            self._plain(f"the part for {stage!r}", text)

    def identifier(self) -> str:
        """The name and version, as people write it: ``plain_style@2``."""
        return f"{self.name}@{self.version}"

    def stages(self) -> tuple[str, ...]:
        """The stages this skill has text for, in order."""
        return tuple(stage for stage, _ in self.parts)

    def part(self, stage: str) -> str | None:
        """The text for the stage, or None when the skill says nothing about it."""
        for named, text in self.parts:
            if named == stage:
                return text
        return None

    @classmethod
    def _plain(cls, label: str, text: str) -> None:
        for char in text:
            if char not in "\n\t" and unicodedata.category(char) in cls.HIDDEN:
                raise ValueError(
                    f"{label} has a character that cannot be seen or is a control: U+{ord(char):04X}"
                )
