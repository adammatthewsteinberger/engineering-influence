# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Ledger repository port."""

from abc import ABC, abstractmethod

from engineering_influence.interfaces.ledger_port import LedgerPort


class LedgerRepositoryInterface(LedgerPort, ABC):
    """Append-only event repository with readback for recovery."""

    @abstractmethod
    def events(self) -> list[tuple[str, dict[str, object]]]:
        """Return events in append order."""
