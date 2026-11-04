"""SQLModel-backed append-only ledger."""

import json

from sqlmodel import Session, SQLModel, col, create_engine, select

from engineering_influence.repositories.interfaces.ledger_repository_interface import (
    LedgerRepositoryInterface,
)
from engineering_influence.repositories.ledger_event_record import LedgerEventRecord


class SqlModelLedger(LedgerRepositoryInterface):
    """Persist ledger events through SQLite or PostgreSQL SQLModel engines."""

    def __init__(self, database_url: str = "sqlite://") -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self._engine = create_engine(database_url, connect_args=connect_args)
        SQLModel.metadata.create_all(self._engine)

    def append(self, event_name: str, payload: dict[str, object]) -> None:
        record = LedgerEventRecord(event_name=event_name, payload_json=json.dumps(payload, sort_keys=True))
        with Session(self._engine) as session:
            session.add(record)
            session.commit()

    def events(self) -> list[tuple[str, dict[str, object]]]:
        with Session(self._engine) as session:
            records = session.exec(
                select(LedgerEventRecord).order_by(col(LedgerEventRecord.id))
            ).all()
        return [(record.event_name, json.loads(record.payload_json)) for record in records]

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._engine.dispose()
