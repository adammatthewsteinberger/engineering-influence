# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A session store that keeps sessions in this process only; for tests and single-process use."""

from engineering_influence.interfaces.acp_session_store_interface import AcpSessionStoreInterface
from engineering_influence.models.acp_session import AcpSession


class InMemoryAcpSessionStore(AcpSessionStoreInterface):
    """Sessions in a dictionary: a new process starts with none."""

    def __init__(self) -> None:
        """Start with no sessions."""
        self._sessions: dict[str, AcpSession] = {}

    def get(self, session_id: str) -> AcpSession | None:
        """The saved session with this id, or None."""
        return self._sessions.get(session_id)

    def save(self, session: AcpSession) -> None:
        """Save the session, replacing any saved under the same id."""
        self._sessions[session.session_id] = session
