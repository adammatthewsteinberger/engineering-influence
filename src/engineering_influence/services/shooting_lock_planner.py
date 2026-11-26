# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Numbers a shooting script: the numbers already locked stay, and each new scene takes the next free one."""

import string
from typing import ClassVar

from engineering_influence.models.shooting_lock import ShootingLock
from engineering_influence.models.shooting_lock_entry import ShootingLockEntry
from engineering_influence.services.interfaces.shooting_lock_planner_interface import (
    ShootingLockPlannerInterface,
)


class ShootingLockPlanner(ShootingLockPlannerInterface):
    """A new scene goes just after the scene before it in the script. At the end of the script it takes the next whole
    number (43 after 42). Anywhere else it takes the next letter that fits (42A, then 42B, after 42). A scene before the
    first locked scene is numbered 0A. A locked scene that the script drops stays in the lock as omitted, and a scene
    that comes back keeps its old number. A locked scene that has moved refuses the plan: a move needs a new lock.
    """

    LETTERS: ClassVar[str] = string.ascii_uppercase
    START: ClassVar[tuple[int, str]] = (0, "")

    def plan(self, previous: ShootingLock, cards: tuple[int, ...]) -> ShootingLock:
        if len(set(cards)) != len(cards):
            raise ValueError("a scene card appears once in the script")
        locked = previous.numbered_cards()
        in_script = set(cards)
        if [card for card in cards if card in locked] != [
            card for card in locked if card in in_script
        ]:
            raise ValueError(
                "a locked scene has moved in the script; a move needs a new shooting script lock"
            )
        entries = [
            ShootingLockEntry(entry.card, entry.label, entry.card not in in_script)
            for entry in previous.entries
        ]
        for index, card in enumerate(cards):
            if any(entry.card == card for entry in entries):
                continue
            before = next(
                (i for i, entry in enumerate(entries) if index and entry.card == cards[index - 1]),
                -1,
            )
            low = entries[before] if before >= 0 else None
            high = entries[before + 1] if before + 1 < len(entries) else None
            entries.insert(before + 1, ShootingLockEntry(card, self._label(low, high), False))
        return ShootingLock(tuple(entries))

    @classmethod
    def _label(cls, low: ShootingLockEntry | None, high: ShootingLockEntry | None) -> str:
        """The first label after `low` that is before `high`; at either end of the script, the open side is free."""
        if high is None:
            return str(low.sort_key()[0] + 1) if low is not None else "1"
        base, after = cls.START if low is None else low.sort_key()
        for letter in cls.LETTERS:
            if (base, letter) > (base, after) and (base, letter) < high.sort_key():
                return f"{base}{letter}"
        if low is not None and (base + 1, "") < high.sort_key():
            return str(base + 1)
        raise ValueError(
            f"no scene number fits between {cls._name(low)} and {high.label}; the script needs a new shooting script lock"
        )

    @staticmethod
    def _name(entry: ShootingLockEntry | None) -> str:
        return "the start" if entry is None else entry.label
