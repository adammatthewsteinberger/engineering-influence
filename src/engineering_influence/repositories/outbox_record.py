# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel record for an outbound webhook intent."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class OutboxRecord(SQLModel, table=True):
    """Durable webhook intent whose delivery can be retried safely."""

    id: int | None = Field(default=None, primary_key=True)
    event_id: str = Field(index=True, unique=True)
    url: str
    event_name: str
    payload_json: str
    delivered_at: datetime | None = None
    attempts: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
