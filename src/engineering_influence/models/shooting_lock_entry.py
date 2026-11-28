# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One scene's place in the locked shooting script: its scene card, the number printed for it, and whether it is omitted."""

import re
import string
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.shooting_lock_entry_interface import (
    ShootingLockEntryInterface,
)


@dataclass(frozen=True, slots=True)
class ShootingLockEntry(ShootingLockEntryInterface):
    """`card` is the scene card's number, which a lock never changes. `label` is the number printed for the scene: a
    whole number such as `42`, or an insert such as `42A`. An omitted scene keeps its label, so no number is reused."""

    LABEL: ClassVar[re.Pattern[str]] = re.compile(r"([0-9]+)([A-Z]?)")

    card: int
    label: str
    omitted: bool

    def __post_init__(self) -> None:
        if type(self.card) is not int or self.card < 1:
            raise ValueError("a locked scene is a scene card numbered from 1")
        if self.LABEL.fullmatch(self.label) is None:
            raise ValueError(
                f"a scene number is a number with at most one capital letter, like 42 or 42A, not {self.label!r}"
            )
        if type(self.omitted) is not bool:
            raise ValueError("a locked scene is either omitted or not")

    def sort_key(self) -> tuple[int, str]:
        """The number and the letter of the label. The constructor has checked the label, so the letter, if any, is its
        last character and the number is what comes before it."""
        digits = self.label.rstrip(string.ascii_uppercase)
        return int(digits), self.label[len(digits) :]
