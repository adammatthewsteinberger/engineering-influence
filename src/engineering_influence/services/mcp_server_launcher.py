# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Starts a locked MCP server for a run, and only if it is still what was approved."""

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.mcp_remote_transport_factory_interface import (
    McpRemoteTransportFactoryInterface,
)
from engineering_influence.interfaces.mcp_transport_factory_interface import (
    McpTransportFactoryInterface,
)
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.services.interfaces.mcp_client_factory_interface import (
    McpClientFactoryInterface,
)
from engineering_influence.services.interfaces.mcp_client_interface import McpClientInterface
from engineering_influence.services.interfaces.mcp_connection_interface import (
    McpConnectionInterface,
)
from engineering_influence.services.interfaces.mcp_server_launcher_interface import (
    McpServerLauncherInterface,
)
from engineering_influence.services.interfaces.tool_lock_verifier_interface import (
    ToolLockVerifierInterface,
)
from engineering_influence.services.mcp_connection import McpConnection


class McpServerLauncher(McpServerLauncherInterface):
    """The start-up check of ADR 0008, in the order it can be made.

    1. **The files**, before anything is started: a server whose files changed is never run. (A remote
       server has no files; its address is checked by the URL policy when it is contacted.)
    2. **The server**, started with the lock's environment names only (or contacted at its address with
       its bearer variable), initialized and asked for its tools.
    3. **What it says**, compared with the lock: its name, its version and the hash of its tools.
    4. **The grants**: a tool the lock grants to a stage must be one that can be offered.

    Any difference stops the server (it is closed, never left running) and raises an error that
    names the server and every problem. A server that cannot be started or does not answer is the same
    refusal: a run does not begin with a tool it was promised and cannot have.
    """

    def __init__(
        self,
        transports: McpTransportFactoryInterface,
        remote: McpRemoteTransportFactoryInterface,
        clients: McpClientFactoryInterface,
        verifier: ToolLockVerifierInterface,
    ) -> None:
        self._transports = transports
        self._remote = remote
        self._clients = clients
        self._verifier = verifier

    def verify_files(self, entry: McpServerLock) -> None:
        """The file check of step 1 alone: nothing is started."""
        self._refuse(entry, self._verifier.check_files(entry))

    def start(self, entry: McpServerLock) -> McpConnectionInterface:
        """Check the files, start the server, check what it says, and return the connection."""
        self._refuse(entry, self._verifier.check_files(entry))
        client: McpClientInterface | None = None
        try:
            client = self._clients.create(self._open(entry))
            info = client.initialize()
            tools = client.list_tools()
            self._refuse(entry, self._verifier.check_server(entry, info, tools))
            skipped = set(tools.skipped(entry.name))
            unusable = sorted({tool for _, granted in entry.grants for tool in granted} & skipped)
            self._refuse(
                entry,
                tuple(
                    f"the granted tool {tool!r} cannot be offered to a model" for tool in unusable
                ),
            )
            return McpConnection(entry.name, client, tools)
        except TransientStageError as error:
            self._close(client)
            raise self._unavailable(entry, str(error)) from error
        except ApplicationError as error:
            self._close(client)
            if error.code == "TOOL_LOCK_MISMATCH":
                raise
            raise self._unavailable(entry, error.message, error.code) from error

    def _open(self, entry: McpServerLock) -> McpTransportInterface:
        if entry.remote():
            return self._remote.open(entry.url, entry.bearer_env)
        return self._transports.open(entry.command, entry.env)

    @staticmethod
    def _close(client: McpClientInterface | None) -> None:
        if client is not None:
            client.close()

    @staticmethod
    def _refuse(entry: McpServerLock, problems: tuple[str, ...]) -> None:
        if problems:
            raise ApplicationError(
                code="TOOL_LOCK_MISMATCH",
                message=f"locked server {entry.name!r} is not what was approved: "
                + "; ".join(problems),
                http_status=503,
            )

    @staticmethod
    def _unavailable(
        entry: McpServerLock, why: str, code: str = "TOOL_SERVER_UNAVAILABLE"
    ) -> ApplicationError:
        return ApplicationError(
            code=code,
            message=f"locked server {entry.name!r} could not be started: {why}",
            http_status=503,
        )
