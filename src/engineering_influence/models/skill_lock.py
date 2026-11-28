# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The skills a person has installed, as written in the skill lock file."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.skill_lock_interface import SkillLockInterface
from engineering_influence.models.skill_lock_entry import SkillLockEntry


@dataclass(frozen=True, slots=True)
class SkillLock(SkillLockInterface):
    """Every installed skill, by name. A run shows a model only the skills enabled here.

    The lock file is a contract: its format is versioned, and an entry changes only when a person
    runs ``ei skills`` and reviews the difference like any other commit. A stage may have at most
    ``MAX_PER_STAGE`` skills enabled, which bounds how much installed text one prompt can carry.
    """

    VERSION: ClassVar[int] = 1
    MAX_PER_STAGE: ClassVar[int] = 4

    entries: tuple[SkillLockEntry, ...] = ()

    def __post_init__(self) -> None:
        """Validate the lock's entries when it is built."""
        if not isinstance(self.entries, tuple):
            raise TypeError("a skill lock is a tuple of entries")
        names = [entry.name for entry in self.entries]
        if len(set(names)) != len(names):
            raise ValueError("two locked skills share a name")
        counts: dict[str, int] = {}
        for entry in self.entries:
            for stage in entry.stages:
                counts[stage] = counts.get(stage, 0) + 1
        for stage, count in sorted(counts.items()):
            if count > self.MAX_PER_STAGE:
                raise ValueError(
                    f"stage {stage!r} would have {count} skills; the most is {self.MAX_PER_STAGE}"
                )

    def entry(self, name: str) -> SkillLockEntry | None:
        """The locked skill with this name, or None."""
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None

    def with_entry(self, entry: SkillLockEntry, replace: bool) -> "SkillLock":
        """This lock with the entry added; an existing one of that name is replaced only if asked."""
        kept = tuple(existing for existing in self.entries if existing.name != entry.name)
        if len(kept) != len(self.entries) and not replace:
            raise ValueError(f"a skill named {entry.name!r} is already locked")
        return SkillLock((*kept, entry))

    def without(self, name: str) -> "SkillLock":
        """This lock with the skill taken out."""
        kept = tuple(entry for entry in self.entries if entry.name != name)
        if len(kept) == len(self.entries):
            raise ValueError(f"no skill named {name!r} is locked")
        return SkillLock(kept)

    def names(self) -> tuple[str, ...]:
        """The locked skills' names, sorted."""
        return tuple(sorted(entry.name for entry in self.entries))

    def enabled(self, stage: str) -> tuple[SkillLockEntry, ...]:
        """The entries enabled for this stage, in name order."""
        found = (entry for entry in self.entries if entry.enabled_for(stage))
        return tuple(sorted(found, key=lambda entry: entry.name))
