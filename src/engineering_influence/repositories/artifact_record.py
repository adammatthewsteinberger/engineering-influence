# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel record for one stored artifact."""

from datetime import UTC, datetime

from sqlalchemy import Column, LargeBinary, UniqueConstraint
from sqlmodel import Field, SQLModel

from engineering_influence.repositories.interfaces.artifact_record_interface import (
    ArtifactRecordInterface,
)


class ArtifactRecord(ArtifactRecordInterface, SQLModel, table=True):
    """An artifact's bytes and digest; one row per run and name."""

    __table_args__ = (UniqueConstraint("run_id", "name"),)

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)
    name: str
    digest: str
    data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
