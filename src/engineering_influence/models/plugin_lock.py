# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The plugins a person has installed, as written in the plugin lock file."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.plugin_lock_interface import PluginLockInterface
from engineering_influence.models.plugin_lock_entry import PluginLockEntry


@dataclass(frozen=True, slots=True)
class PluginLock(PluginLockInterface):
    """Every installed plugin, by name.

    The plugin lock is a record, not a permission: **a run never reads it**. What a run may do is in
    the tool lock and the skill lock, which a plugin only adds entries to (skills, with no stage
    enabled) or prints commands for (servers). The plugin lock is what lets ``ei plugins verify``
    check the bundle that was reviewed and ``ei plugins remove`` undo what it installed.
    """

    VERSION: ClassVar[int] = 1

    entries: tuple[PluginLockEntry, ...] = ()

    def __post_init__(self) -> None:
        """Validate the lock's entries when it is built."""
        if not isinstance(self.entries, tuple):
            raise TypeError("a plugin lock is a tuple of entries")
        names = [entry.name for entry in self.entries]
        if len(set(names)) != len(names):
            raise ValueError("two locked plugins share a name")

    def entry(self, name: str) -> PluginLockEntry | None:
        """The locked plugin with this name, or None."""
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None

    def with_entry(self, entry: PluginLockEntry) -> "PluginLock":
        """This lock with the entry added; a plugin that is already installed is not replaced."""
        if self.entry(entry.name) is not None:
            raise ValueError(f"a plugin named {entry.name!r} is already installed")
        return PluginLock((*self.entries, entry))

    def without(self, name: str) -> "PluginLock":
        """This lock with the plugin taken out."""
        kept = tuple(entry for entry in self.entries if entry.name != name)
        if len(kept) == len(self.entries):
            raise ValueError(f"no plugin named {name!r} is installed")
        return PluginLock(kept)

    def names(self) -> tuple[str, ...]:
        """The installed plugins' names, sorted."""
        return tuple(sorted(entry.name for entry in self.entries))
