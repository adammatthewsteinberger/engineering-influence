# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel record for one Agent Client Protocol session."""

from sqlmodel import Field, SQLModel

from engineering_influence.repositories.interfaces.acp_session_record_interface import (
    AcpSessionRecordInterface,
)


class AcpSessionRecord(AcpSessionRecordInterface, SQLModel, table=True):
    """One row per session; the run is empty until the first prompt starts one. ``servers`` is the selected server names,
    as a JSON list, and is empty for a session that selected none (migration 0003 backfills that)."""

    session_id: str = Field(primary_key=True)
    cwd: str
    run_id: str | None = None
    servers: str = "[]"
    approved: str = "[]"
