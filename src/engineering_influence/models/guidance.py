# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The installed text a stage's prompt carries, and the name that goes in the journal key."""

import re
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.guidance_interface import GuidanceInterface


@dataclass(frozen=True, slots=True)
class Guidance(GuidanceInterface):
    """What the skills enabled for a stage add to its prompt.

    ``text`` is added to the end of the stage's prompt. ``identity`` names exactly which skills
    and which frame produced it, and is added to the prompt version, so a resumed run reuses an
    answer only when the same text was in the prompt. A stage with no skills has neither.

    ``tools`` are the names of the built-in tools the text refers to (``read_skill``, when a skill
    has reference sections). A stage is offered them in addition to its own, so the text never points
    at a tool the model was not given. A stage with no text needs no tools.
    """

    NAME: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]*")

    text: str = ""
    identity: str = ""
    tools: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not isinstance(self.identity, str):
            raise TypeError("guidance is text and the name of where it came from")
        if bool(self.text) != bool(self.identity):
            raise ValueError("guidance has text and an identity, or neither")
        if self.text and not self.text.strip():
            raise ValueError("guidance text is more than blank space")
        if not isinstance(self.tools, tuple) or any(
            not isinstance(name, str) or not self.NAME.fullmatch(name) for name in self.tools
        ):
            raise ValueError("guidance names its tools as a tuple of tool names")
        if self.tools and not self.text:
            raise ValueError("guidance with no text needs no tools")
        if len(set(self.tools)) != len(self.tools):
            raise ValueError("guidance names each tool once")

    def empty(self) -> bool:
        """Whether there is nothing to add to the prompt."""
        return not self.text
