# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel record for the saved state of one book run."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from engineering_influence.repositories.interfaces.book_run_record_interface import (
    BookRunRecordInterface,
)


class BookRunRecord(BookRunRecordInterface, SQLModel, table=True):
    """One row per run; status and stage are columns so runs can be listed without decoding."""

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True, unique=True)
    status: str
    stage: str
    document_json: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
