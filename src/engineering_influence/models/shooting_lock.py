# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The locked scenes of a shooting script: each scene's number, in script order, omitted scenes included."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.shooting_lock_interface import ShootingLockInterface
from engineering_influence.models.shooting_lock_entry import ShootingLockEntry


@dataclass(frozen=True, slots=True)
class ShootingLock(ShootingLockInterface):
    """Entries run in script order, so a later scene never carries a smaller number than an earlier one. Each card and
    each label appears once: a number that was printed once is never printed for another scene."""

    entries: tuple[ShootingLockEntry, ...] = ()

    def __post_init__(self) -> None:
        """Validate that the entries run in script order, with each card and label checked."""
        cards = [entry.card for entry in self.entries]
        labels = [entry.label for entry in self.entries]
        if len(set(cards)) != len(cards):
            raise ValueError("a scene card is locked once")
        if len(set(labels)) != len(labels):
            raise ValueError("a scene number is used once")
        keys = [entry.sort_key() for entry in self.entries]
        if keys != sorted(keys):
            raise ValueError("the scene numbers run in script order")

    def numbered_cards(self) -> tuple[int, ...]:
        """Every locked scene card, in script order, omitted scenes included."""
        return tuple(entry.card for entry in self.entries)
