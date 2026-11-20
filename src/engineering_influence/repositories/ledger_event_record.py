# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel persistence record for one ledger event."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from engineering_influence.repositories.interfaces.ledger_event_record_interface import (
    LedgerEventRecordInterface,
)


class LedgerEventRecord(LedgerEventRecordInterface, SQLModel, table=True):
    """Immutable event row used by the durable ledger adapter."""

    id: int | None = Field(default=None, primary_key=True)
    event_name: str
    payload_json: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
