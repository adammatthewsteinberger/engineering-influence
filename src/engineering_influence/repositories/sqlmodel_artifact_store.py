# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel-backed artifact store, for runs whose workers do not share a disk."""

import hashlib

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, col, create_engine, select

from engineering_influence.errors.artifact_conflict_error import ArtifactConflictError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.models.artifact_address import ArtifactAddress
from engineering_influence.repositories.artifact_record import ArtifactRecord


class SqlModelArtifactStore(ArtifactStoreInterface):
    """Persist artifacts as rows; the database refuses a second row for the same run and name."""

    def __init__(self, database_url: str = "sqlite://") -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self._engine = create_engine(database_url, connect_args=connect_args)
        SQLModel.metadata.create_all(self._engine)

    def put(self, run_id: str, name: str, data: bytes) -> str:
        address = ArtifactAddress(run_id, name)
        digest = hashlib.sha256(data).hexdigest()
        existing = self._stored_digest(run_id, name)
        if existing is not None:
            return self._same_or_conflict(existing, digest, address)
        try:
            with Session(self._engine) as session:
                session.add(ArtifactRecord(run_id=run_id, name=name, digest=digest, data=data))
                session.commit()
        except IntegrityError:
            # Another worker stored this name between our look and our insert.
            winner = self._stored_digest(run_id, name)
            if winner is None:
                raise RuntimeError(
                    "the store refused a duplicate artifact but cannot find the original"
                ) from None
            return self._same_or_conflict(winner, digest, address)
        return digest

    def get(self, run_id: str, name: str) -> bytes | None:
        ArtifactAddress(run_id, name)
        with Session(self._engine) as session:
            row = session.exec(
                select(ArtifactRecord)
                .where(ArtifactRecord.run_id == run_id)
                .where(ArtifactRecord.name == name)
            ).first()
        return None if row is None else row.data

    def names(self, run_id: str) -> list[str]:
        ArtifactAddress(run_id, "x")
        with Session(self._engine) as session:
            return list(
                session.exec(
                    select(ArtifactRecord.name)
                    .where(ArtifactRecord.run_id == run_id)
                    .order_by(col(ArtifactRecord.name))
                ).all()
            )

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._engine.dispose()

    def _stored_digest(self, run_id: str, name: str) -> str | None:
        with Session(self._engine) as session:
            return session.exec(
                select(ArtifactRecord.digest)
                .where(ArtifactRecord.run_id == run_id)
                .where(ArtifactRecord.name == name)
            ).first()

    def _same_or_conflict(self, stored: str, digest: str, address: ArtifactAddress) -> str:
        if stored != digest:
            raise ArtifactConflictError(f"{address.relative_path()} already holds different bytes")
        return digest
