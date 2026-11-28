# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A session of the Agent Client Protocol: where it works, which run its first prompt started, and which locked MCP
servers it selected."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.acp_session_interface import AcpSessionInterface
from engineering_influence.models.mcp_server_lock import McpServerLock


@dataclass(frozen=True, slots=True)
class AcpSession(AcpSessionInterface):
    """The session id, its absolute working directory, the run id once a prompt has started one, and the names of the
    locked MCP servers the session selected. A name is only ever one the operator's lock names."""

    session_id: str
    cwd: str
    run_id: str | None = None
    servers: tuple[str, ...] = ()
    # The selected servers the person approved for this session, each once; a server is approved before it starts.
    approved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise ValueError("a session needs an id")
        if not self.cwd.startswith("/"):
            raise ValueError("a session's working directory is an absolute path")
        if any(not McpServerLock.NAME.fullmatch(name) for name in self.servers):
            raise ValueError("a selected server name must be a locked server's name")
        if len(set(self.servers)) != len(self.servers):
            raise ValueError("a session selects each server once")
        if not set(self.approved) <= set(self.servers) or len(set(self.approved)) != len(
            self.approved
        ):
            raise ValueError("a session approves each selected server once, and no other")
