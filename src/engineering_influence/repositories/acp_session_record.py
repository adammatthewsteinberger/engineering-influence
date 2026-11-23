# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel record for one Agent Client Protocol session."""

from sqlmodel import Field, SQLModel

from engineering_influence.repositories.interfaces.acp_session_record_interface import (
    AcpSessionRecordInterface,
)


class AcpSessionRecord(AcpSessionRecordInterface, SQLModel, table=True):
    """One row per session; the run is empty until the first prompt starts one."""

    session_id: str = Field(primary_key=True)
    cwd: str
    run_id: str | None = None
