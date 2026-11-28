# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A Claude Code marketplace, read only as a list to look at."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.marketplace_listing_interface import (
    MarketplaceListingInterface,
)
from engineering_influence.models.marketplace_entry import MarketplaceEntry


@dataclass(frozen=True, slots=True)
class MarketplaceListing(MarketplaceListingInterface):
    """Its name, the entries that could be read, and how many could not.

    It vouches for nothing and carries nothing that can be run: a listing is how a person learns what to look at, and
    getting a plugin from it is the person's own step (clone it, read it, ``ei plugins import`` it). Entries are in
    name order, each name once, at most ``MAX_ENTRIES``.
    """

    MAX_ENTRIES: ClassVar[int] = 500

    name: str
    entries: tuple[MarketplaceEntry, ...] = ()
    unreadable: int = 0

    def __post_init__(self) -> None:
        """Validate the listing's entries when it is built."""
        if not isinstance(self.name, str) or not self.name.strip() or not self.name.isprintable():
            raise ValueError("a marketplace has a one-line name")
        if not isinstance(self.entries, tuple) or len(self.entries) > self.MAX_ENTRIES:
            raise ValueError(f"a listing is a tuple of at most {self.MAX_ENTRIES} entries")
        names = [entry.name for entry in self.entries]
        if names != sorted(set(names)):
            raise ValueError("a listing names each plugin once, in name order")
        if type(self.unreadable) is not int or self.unreadable < 0:
            raise ValueError("the number of unreadable entries is a whole number from 0")

    def search(self, text: str) -> tuple[MarketplaceEntry, ...]:
        """The entries whose name or description contains the text, ignoring case; all of them for no text."""
        needle = text.strip().lower()
        return tuple(
            entry
            for entry in self.entries
            if needle in entry.name.lower() or needle in entry.description.lower()
        )
