# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A marketplace index: a list of plugin files, each with an address and a hash."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.plugin_index_interface import PluginIndexInterface
from engineering_influence.models.plugin_index_entry import PluginIndexEntry


@dataclass(frozen=True, slots=True)
class PluginIndex(PluginIndexInterface):
    """Only an index (ADR 0008, decision 9): it lists plugin files and vouches for none of them.

    It has no code, no skill text and no server definition, only names, versions, descriptions,
    addresses and hashes. Finding a plugin in one is how a person learns what to look at; trusting it is
    a separate step the person takes by reading the file and installing it. Entries are unique by name
    and in name order, and there are at most ``MAX_ENTRIES``.
    """

    VERSION: ClassVar[int] = 1
    MAX_ENTRIES: ClassVar[int] = 500

    entries: tuple[PluginIndexEntry, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.entries, tuple):
            raise TypeError("an index is a tuple of entries")
        if len(self.entries) > self.MAX_ENTRIES:
            raise ValueError(f"an index lists at most {self.MAX_ENTRIES} plugins")
        names = [entry.name for entry in self.entries]
        if names != sorted(set(names)):
            raise ValueError("an index lists each plugin once, in name order")

    def find(self, name: str) -> PluginIndexEntry | None:
        """The entry with this name, or None."""
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None

    def search(self, text: str) -> tuple[PluginIndexEntry, ...]:
        """The entries whose name or description contains the text, ignoring case; all of them for no text."""
        needle = text.strip().lower()
        return tuple(
            entry
            for entry in self.entries
            if needle in entry.name.lower() or needle in entry.description.lower()
        )
