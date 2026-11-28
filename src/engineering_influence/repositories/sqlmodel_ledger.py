# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel-backed append-only ledger."""

import json

from sqlmodel import Session, col, create_engine, select

from engineering_influence.interfaces.ledger_repository_interface import (
    LedgerRepositoryInterface,
)
from engineering_influence.repositories.ledger_event_record import LedgerEventRecord


class SqlModelLedger(LedgerRepositoryInterface):
    """Persist ledger events through SQLite or PostgreSQL SQLModel engines."""

    def __init__(self, database_url: str) -> None:
        """Remember the database that holds the ledger events."""
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self._engine = create_engine(database_url, connect_args=connect_args)

    def append(self, event_name: str, payload: dict[str, object]) -> None:
        """Record an event with its payload as JSON."""
        record = LedgerEventRecord(
            event_name=event_name, payload_json=json.dumps(payload, sort_keys=True)
        )
        with Session(self._engine) as session:
            session.add(record)
            session.commit()

    def events(self) -> list[tuple[str, dict[str, object]]]:
        """Every recorded event with its payload, in the order they were recorded."""
        with Session(self._engine) as session:
            records = session.exec(
                select(LedgerEventRecord).order_by(col(LedgerEventRecord.id))
            ).all()
        return [(record.event_name, json.loads(record.payload_json)) for record in records]

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._engine.dispose()
