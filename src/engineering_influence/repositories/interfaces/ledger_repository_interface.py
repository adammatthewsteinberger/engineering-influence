"""Ledger repository port."""

from abc import ABC, abstractmethod

from engineering_influence.interfaces.ledger_port import LedgerPort


class LedgerRepositoryInterface(LedgerPort, ABC):
    """Append-only event repository with readback for recovery."""

    @abstractmethod
    def events(self) -> list[tuple[str, dict[str, object]]]:
        """Return events in append order."""
