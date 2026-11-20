# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for LedgerEventRecord."""

from abc import ABC


class LedgerEventRecordInterface(ABC):
    """Immutable event row used by the durable ledger adapter."""

    __slots__ = ()
