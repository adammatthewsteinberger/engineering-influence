# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SQLModel-backed store for Agent Client Protocol sessions."""

import json

from sqlalchemy.pool import NullPool
from sqlmodel import Session, create_engine

from engineering_influence.interfaces.acp_session_store_interface import AcpSessionStoreInterface
from engineering_influence.models.acp_session import AcpSession
from engineering_influence.repositories.acp_session_record import AcpSessionRecord


class SqlModelAcpSessionStore(AcpSessionStoreInterface):
    """Sessions in the same database as the runs, so any process can load a session another started."""

    def __init__(self, database_url: str, pooled: bool = True) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self._engine = create_engine(
            database_url, connect_args=connect_args, **({} if pooled else {"poolclass": NullPool})
        )

    def get(self, session_id: str) -> AcpSession | None:
        with Session(self._engine) as session:
            record = session.get(AcpSessionRecord, session_id)
            if record is None:
                return None
            servers = tuple(json.loads(record.servers))
            approved = tuple(json.loads(record.approved))
            return AcpSession(record.session_id, record.cwd, record.run_id, servers, approved)

    def save(self, acp_session: AcpSession) -> None:
        with Session(self._engine) as session:
            record = session.get(AcpSessionRecord, acp_session.session_id)
            if record is None:
                record = AcpSessionRecord(session_id=acp_session.session_id, cwd=acp_session.cwd)
            record.cwd = acp_session.cwd
            record.run_id = acp_session.run_id
            record.servers = json.dumps(list(acp_session.servers))
            record.approved = json.dumps(list(acp_session.approved))
            session.add(record)
            session.commit()
