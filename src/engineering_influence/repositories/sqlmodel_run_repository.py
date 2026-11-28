# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel-backed run repository."""

import json
from datetime import UTC, datetime

from sqlalchemy.pool import NullPool
from sqlmodel import Session, col, create_engine, select, update

from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.outbox_event import OutboxEvent
from engineering_influence.repositories.book_run_codec import BookRunCodec
from engineering_influence.repositories.book_run_record import BookRunRecord
from engineering_influence.repositories.outbox_record import OutboxRecord


class SqlModelRunRepository(RunRepositoryInterface):
    """Persist runs through SQLite or PostgreSQL, one row per run, replaced on every save."""

    def __init__(self, database_url: str, pooled: bool = True) -> None:
        """Remember the database; each run is one row, replaced on every save."""
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self._engine = create_engine(
            database_url, connect_args=connect_args, **({} if pooled else {"poolclass": NullPool})
        )
        self._codec = BookRunCodec()

    def save(self, run: BookRun) -> None:
        """Save the run, replacing any saved under the same id."""
        self.save_with_events(run, ())

    def save_with_events(self, run: BookRun, events: tuple[OutboxEvent, ...]) -> None:
        """Save the run and queue each event whose key has not been queued before."""
        with Session(self._engine) as session:
            record = session.exec(
                select(BookRunRecord).where(BookRunRecord.run_id == run.run_id)
            ).first()
            if record is None:
                record = BookRunRecord(run_id=run.run_id, status="", stage="", document_json="")
            record.status = run.status.value
            record.stage = run.stage
            record.document_json = self._codec.encode(run)
            record.updated_at = datetime.now(UTC)
            session.add(record)
            self._queue(session, events)
            session.commit()

    @staticmethod
    def _queue(session: Session, events: tuple[OutboxEvent, ...]) -> None:
        """Add each event not already queued to the session, so it commits with the caller's change."""
        for event in events:
            already = session.exec(
                select(OutboxRecord).where(OutboxRecord.event_id == event.record_key())
            ).first()
            if already is None:
                session.add(
                    OutboxRecord(
                        event_id=event.event_id,
                        url=event.url,
                        event_name=event.event_name,
                        payload_json=json.dumps(event.payload, sort_keys=True),
                    )
                )

    def swap(self, expected: BookRun, replacement: BookRun) -> bool:
        """Replace the saved run with the replacement only if it is still the expected run; return whether it was replaced."""
        return self.swap_with_events(expected, replacement, ())

    def swap_with_events(
        self, expected: BookRun, replacement: BookRun, events: tuple[OutboxEvent, ...]
    ) -> bool:
        """Replace the saved run only if it is still the expected run, and queue the events in the same transaction."""
        if replacement.run_id != expected.run_id:
            raise ValueError("a swap cannot change the run id")
        with Session(self._engine) as session:
            result = session.exec(
                update(BookRunRecord)
                .where(col(BookRunRecord.run_id) == expected.run_id)
                .where(col(BookRunRecord.document_json) == self._codec.encode(expected))
                .values(
                    status=replacement.status.value,
                    stage=replacement.stage,
                    document_json=self._codec.encode(replacement),
                    updated_at=datetime.now(UTC),
                )
            )
            if result.rowcount != 1:
                session.rollback()
                return False
            self._queue(session, events)
            session.commit()
            return True

    def get(self, run_id: str) -> BookRun | None:
        """The saved run with this id, or None."""
        with Session(self._engine) as session:
            record = session.exec(
                select(BookRunRecord).where(BookRunRecord.run_id == run_id)
            ).first()
        return None if record is None else self._codec.decode(record.document_json)

    def run_ids(self) -> list[str]:
        """The ids of every saved run, sorted."""
        with Session(self._engine) as session:
            return list(
                session.exec(select(BookRunRecord.run_id).order_by(col(BookRunRecord.run_id))).all()
            )

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._engine.dispose()
