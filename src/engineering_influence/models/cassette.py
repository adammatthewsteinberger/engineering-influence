# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A named, ordered list of recorded exchanges with one model provider."""

import re
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.cassette_interaction import CassetteInteraction
from engineering_influence.models.interfaces.cassette_interface import CassetteInterface


@dataclass(frozen=True, slots=True)
class Cassette(CassetteInterface):
    """The exchanges one test replays, in the order the code made them.

    A cassette is made only from synthetic briefs and holds no header, so no key. ``note`` says
    what it was recorded from (the brief, the model, the date) for the next person to re-record it.
    """

    NAME: ClassVar[re.Pattern[str]] = re.compile(r"[a-z0-9][a-z0-9_-]*")

    name: str
    provider: str
    interactions: tuple[CassetteInteraction, ...]
    note: str = ""

    def __post_init__(self) -> None:
        """Validate the cassette's exchanges when it is built."""
        if not self.NAME.fullmatch(self.name):
            raise ValueError(
                f"{self.name!r} is not a cassette name (lower-case letters, digits, - _)"
            )
        if not self.provider.strip():
            raise ValueError("a cassette names its provider")
        if not isinstance(self.interactions, tuple) or not self.interactions:
            raise ValueError("a cassette holds at least one interaction, in a tuple")

    def interaction_at(self, position: int) -> CassetteInteraction | None:
        """The exchange at this position (counting from 0), or None once they are all used."""
        if 0 <= position < len(self.interactions):
            return self.interactions[position]
        return None
