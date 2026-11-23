# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: turning a Claude Code ``marketplace.json`` into a listing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.marketplace_listing import MarketplaceListing


class MarketplaceListingParserInterface(ABC):
    """Reads a marketplace file's bytes as a list of plugins, and as nothing else."""

    __slots__ = ()

    @abstractmethod
    def parse(self, data: bytes) -> MarketplaceListing:
        """The listing, or an ApplicationError (MARKETPLACE_INVALID) saying why the file is not one."""
