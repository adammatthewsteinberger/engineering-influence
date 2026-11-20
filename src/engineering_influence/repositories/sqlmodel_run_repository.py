# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel-backed run repository."""

from datetime import UTC, datetime

from sqlmodel import Session, SQLModel, col, create_engine, select

from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.repositories.book_run_codec import BookRunCodec
from engineering_influence.repositories.book_run_record import BookRunRecord


class SqlModelRunRepository(RunRepositoryInterface):
    """Persist runs through SQLite or PostgreSQL, one row per run, replaced on every save."""

    def __init__(self, database_url: str = "sqlite://") -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self._engine = create_engine(database_url, connect_args=connect_args)
        self._codec = BookRunCodec()
        SQLModel.metadata.create_all(self._engine)

    def save(self, run: BookRun) -> None:
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
            session.commit()

    def get(self, run_id: str) -> BookRun | None:
        with Session(self._engine) as session:
            record = session.exec(
                select(BookRunRecord).where(BookRunRecord.run_id == run_id)
            ).first()
        return None if record is None else self._codec.decode(record.document_json)

    def run_ids(self) -> list[str]:
        with Session(self._engine) as session:
            return list(
                session.exec(select(BookRunRecord.run_id).order_by(col(BookRunRecord.run_id))).all()
            )

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._engine.dispose()
