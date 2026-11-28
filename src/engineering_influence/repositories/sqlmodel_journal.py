# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel-backed run journal."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, create_engine, select

from engineering_influence.interfaces.journal_interface import JournalInterface
from engineering_influence.models.journal_entry import JournalEntry
from engineering_influence.models.journal_key import JournalKey
from engineering_influence.repositories.journal_record import JournalRecord


class SqlModelJournal(JournalInterface):
    """Persist journal entries; the database refuses a second entry for the same request."""

    def __init__(self, database_url: str) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self._engine = create_engine(database_url, connect_args=connect_args)

    def record(self, entry: JournalEntry) -> JournalEntry:
        digest = entry.key.digest()
        existing = self.find(entry.run_id, entry.stage, digest)
        if existing is not None:
            return existing
        try:
            with Session(self._engine) as session:
                session.add(self._row(entry, digest))
                session.commit()
        except IntegrityError:
            # Another worker recorded the same request between our look and our insert.
            winner = self.find(entry.run_id, entry.stage, digest)
            if winner is None:
                raise RuntimeError(
                    "the journal refused a duplicate entry but cannot find the original"
                )
            return winner
        return entry

    def spend(self, entry: JournalEntry) -> None:
        """Count a paid call whose answer another worker recorded first. The row takes its own digest, so a replay still
        finds the first entry for the request, and the cost is part of the run's spend."""
        with Session(self._engine) as session:
            session.add(self._row(entry, f"{entry.key.digest()}:copy:{uuid.uuid4().hex}"))
            session.commit()

    def find(self, run_id: str, stage: str, digest: str) -> JournalEntry | None:
        with Session(self._engine) as session:
            row = session.exec(
                select(JournalRecord)
                .where(JournalRecord.run_id == run_id)
                .where(JournalRecord.stage == stage)
                .where(JournalRecord.digest == digest)
            ).first()
        return None if row is None else self._entry(row)

    def entries(self, run_id: str) -> list[JournalEntry]:
        with Session(self._engine) as session:
            rows = session.exec(
                select(JournalRecord)
                .where(JournalRecord.run_id == run_id)
                .order_by(col(JournalRecord.id))
            ).all()
        return [self._entry(row) for row in rows]

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._engine.dispose()

    def _row(self, entry: JournalEntry, digest: str) -> JournalRecord:
        return JournalRecord(
            run_id=entry.run_id,
            stage=entry.stage,
            attempt=entry.attempt,
            digest=digest,
            model=entry.key.model,
            params_hash=entry.key.params_hash,
            prompt_version=entry.key.prompt_version,
            context_hash=entry.key.context_hash,
            response=entry.response,
            cost_micro_usd=entry.cost_micro_usd,
        )

    def _entry(self, row: JournalRecord) -> JournalEntry:
        return JournalEntry(
            run_id=row.run_id,
            stage=row.stage,
            attempt=row.attempt,
            key=JournalKey(
                model=row.model,
                params_hash=row.params_hash,
                prompt_version=row.prompt_version,
                context_hash=row.context_hash,
            ),
            response=row.response,
            cost_micro_usd=row.cost_micro_usd,
        )
