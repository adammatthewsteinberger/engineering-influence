"""SQLModel-backed webhook outbox."""

import json
from datetime import UTC, datetime

from sqlmodel import Session, SQLModel, col, create_engine, select

from engineering_influence.repositories.interfaces.outbox_repository_interface import (
    OutboxRepositoryInterface,
)
from engineering_influence.repositories.outbox_record import OutboxRecord


class SqlModelOutbox(OutboxRepositoryInterface):
    """Persist idempotent webhook intents with retry metadata."""

    def __init__(self, database_url: str = "sqlite://") -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self._engine = create_engine(database_url, connect_args=connect_args)
        SQLModel.metadata.create_all(self._engine)

    def enqueue(
        self,
        event_id: str,
        url: str,
        event_name: str,
        payload: dict[str, object],
    ) -> None:
        with Session(self._engine) as session:
            existing = session.exec(
                select(OutboxRecord).where(OutboxRecord.event_id == event_id)
            ).first()
            if existing is None:
                session.add(
                    OutboxRecord(
                        event_id=event_id,
                        url=url,
                        event_name=event_name,
                        payload_json=json.dumps(payload, sort_keys=True),
                    )
                )
                session.commit()

    def pending(self) -> list[tuple[str, str, str, dict[str, object], int]]:
        with Session(self._engine) as session:
            records = session.exec(
                select(OutboxRecord)
                .where(OutboxRecord.delivered_at == None)
                .order_by(col(OutboxRecord.id))
            ).all()
        return [
            (
                record.event_id,
                record.url,
                record.event_name,
                json.loads(record.payload_json),
                record.attempts,
            )
            for record in records
        ]

    def mark_delivered(self, event_id: str) -> None:
        with Session(self._engine) as session:
            record = session.exec(
                select(OutboxRecord).where(OutboxRecord.event_id == event_id)
            ).one()
            record.delivered_at = datetime.now(UTC)
            record.attempts += 1
            session.add(record)
            session.commit()

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._engine.dispose()
