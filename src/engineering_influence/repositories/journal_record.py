# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel record for one journal entry."""

from datetime import UTC, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from engineering_influence.repositories.interfaces.journal_record_interface import (
    JournalRecordInterface,
)


class JournalRecord(JournalRecordInterface, SQLModel, table=True):
    """A request is recorded once per run and stage; the unique constraint enforces it."""

    __table_args__ = (UniqueConstraint("run_id", "stage", "digest"),)

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)
    stage: str
    attempt: int
    digest: str
    model: str
    params_hash: str
    prompt_version: str
    context_hash: str
    response: str
    cost_micro_usd: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
