# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The installed text a stage's prompt carries, and the name that goes in the journal key."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.guidance_interface import GuidanceInterface


@dataclass(frozen=True, slots=True)
class Guidance(GuidanceInterface):
    """What the skills enabled for a stage add to its prompt.

    ``text`` is added to the end of the stage's prompt. ``identity`` names exactly which skills
    and which frame produced it, and is added to the prompt version, so a resumed run reuses an
    answer only when the same text was in the prompt. A stage with no skills has neither.
    """

    text: str = ""
    identity: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not isinstance(self.identity, str):
            raise TypeError("guidance is text and the name of where it came from")
        if bool(self.text) != bool(self.identity):
            raise ValueError("guidance has text and an identity, or neither")
        if self.text and not self.text.strip():
            raise ValueError("guidance text is more than blank space")

    def empty(self) -> bool:
        """Whether there is nothing to add to the prompt."""
        return not self.text
