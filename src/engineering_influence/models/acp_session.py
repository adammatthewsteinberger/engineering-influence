# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A session of the Agent Client Protocol: where it works, and which run its first prompt started."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.acp_session_interface import AcpSessionInterface


@dataclass(frozen=True, slots=True)
class AcpSession(AcpSessionInterface):
    """The session id, its absolute working directory, and the run id once a prompt has started one."""

    session_id: str
    cwd: str
    run_id: str | None = None

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise ValueError("a session needs an id")
        if not self.cwd.startswith("/"):
            raise ValueError("a session's working directory is an absolute path")
