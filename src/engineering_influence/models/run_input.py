# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A block of text a person gave a run: notes, an excerpt, a draft, reference material."""

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.run_input_interface import RunInputInterface
from engineering_influence.models.skill import Skill


@dataclass(frozen=True, slots=True)
class RunInput(RunInputInterface):
    """A name, its text, and where it came from (``pasted`` or ``file``).

    It is **untrusted data**: a person gave it, but it may be a page they copied or a file somebody else wrote, so
    it reaches a prompt only as evidence in an ``<untrusted>`` block and can never widen what a stage may call. The text
    is plain: a line break and a tab are allowed, and any other control, format, private-use or invisible character is
    refused (the same rule a skill's text is held to), so what was read by a person is what a model sees. It is at
    most ``MAX_TEXT_CHARS`` characters and is never cut to fit.
    """

    NAME: ClassVar[re.Pattern[str]] = re.compile(r"[a-z0-9][a-z0-9_.-]{0,59}")
    ORIGINS: ClassVar[frozenset[str]] = frozenset({"pasted", "file"})
    MAX_TEXT_CHARS: ClassVar[int] = 50_000

    name: str
    text: str
    origin: str = "pasted"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.NAME.fullmatch(self.name):
            raise ValueError(
                "an input's name is lowercase letters, digits, dots, hyphens and underscores, "
                "starting with a letter or digit, at most 60"
            )
        if self.origin not in self.ORIGINS:
            raise ValueError(f"an input comes from one of {sorted(self.ORIGINS)}")
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError(f"input {self.name!r} has text")
        if len(self.text) > self.MAX_TEXT_CHARS:
            raise ValueError(
                f"input {self.name!r} is {len(self.text):,} characters; the most is {self.MAX_TEXT_CHARS:,}"
            )
        for char in self.text:
            if char not in "\n\t" and self._unseen(char):
                raise ValueError(
                    f"input {self.name!r} has a character that cannot be seen or is a control: U+{ord(char):04X}"
                )

    def digest(self) -> str:
        """The SHA-256 of the text."""
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def block(self) -> str:
        """The input as it is shown to a model: a heading naming it and its origin and digest, then the text.

        The heading is made only of the validated name and origin and a hex digest, so it cannot carry text of its own.
        """
        return f"### {self.name} ({self.origin}, sha256 {self.digest()[:12]})\n\n{self.text}"

    @staticmethod
    def _unseen(char: str) -> bool:
        point = ord(char)
        return (
            any(low <= point <= high for low, high in Skill.INVISIBLE)
            or unicodedata.category(char) in Skill.HIDDEN
        )
