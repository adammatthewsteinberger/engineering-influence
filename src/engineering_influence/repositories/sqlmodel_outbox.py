# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel-backed webhook outbox."""

import json
from datetime import UTC, datetime

from sqlmodel import Session, col, create_engine, select

from engineering_influence.interfaces.outbox_interface import (
    OutboxInterface,
)
from engineering_influence.repositories.outbox_record import OutboxRecord


class SqlModelOutbox(OutboxInterface):
    """Persist idempotent webhook intents with retry metadata."""

    def __init__(self, database_url: str) -> None:
        """Remember the database that holds the webhook intents."""
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self._engine = create_engine(database_url, connect_args=connect_args)

    def enqueue(
        self,
        event_id: str,
        url: str,
        event_name: str,
        payload: dict[str, object],
    ) -> None:
        """Queue an event for delivery to a URL, unless an event with the same id is already queued."""
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
        """The events not yet delivered or dead, in queue order, with their attempts so far."""
        with Session(self._engine) as session:
            records = session.exec(
                select(OutboxRecord)
                .where(OutboxRecord.delivered_at == None)
                .where(OutboxRecord.dead_at == None)
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
        """Record that the event was delivered, counting the attempt."""
        with Session(self._engine) as session:
            record = session.exec(
                select(OutboxRecord).where(OutboxRecord.event_id == event_id)
            ).one()
            record.delivered_at = datetime.now(UTC)
            record.attempts += 1
            session.add(record)
            session.commit()

    def mark_failed(self, event_id: str) -> int:
        """Count a failed delivery attempt and return the attempts so far."""
        with Session(self._engine) as session:
            record = session.exec(
                select(OutboxRecord).where(OutboxRecord.event_id == event_id)
            ).one()
            record.attempts += 1
            session.add(record)
            session.commit()
            return record.attempts

    def mark_dead(self, event_id: str) -> None:
        """Mark the event dead: it will not be delivered again."""
        with Session(self._engine) as session:
            record = session.exec(
                select(OutboxRecord).where(OutboxRecord.event_id == event_id)
            ).one()
            record.dead_at = datetime.now(UTC)
            session.add(record)
            session.commit()

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._engine.dispose()
