# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Deterministic in-memory ledger for local CLI and tests."""

from engineering_influence.interfaces.ledger_interface import LedgerInterface


class InMemoryLedger(LedgerInterface):
    """Append-only ledger adapter used for local demonstrations."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def append(self, event_name: str, payload: dict[str, object]) -> None:
        self.events.append((event_name, dict(payload)))
