# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Starts a server just long enough to ask it who it is and what it offers."""

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.mcp_transport_factory_interface import (
    McpTransportFactoryInterface,
)
from engineering_influence.models.mcp_server_inspection import McpServerInspection
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.services.interfaces.mcp_client_factory_interface import (
    McpClientFactoryInterface,
)
from engineering_influence.services.interfaces.mcp_server_probe_interface import (
    McpServerProbeInterface,
)
from engineering_influence.services.interfaces.tool_lock_verifier_interface import (
    ToolLockVerifierInterface,
)


class McpServerProbe(McpServerProbeInterface):
    """The one place a server is started to be looked at.

    ``inspect`` starts the command, initializes, lists the tools and always stops the server, even
    when asking fails. ``check`` is the verification of a lock: the locked files are compared first,
    and **a server whose files have changed is never started**; only then is it started and its
    report compared. A server that cannot be started or does not answer is a problem, not a crash,
    so a check of several servers reports all of them.
    """

    def __init__(
        self,
        transports: McpTransportFactoryInterface,
        clients: McpClientFactoryInterface,
        verifier: ToolLockVerifierInterface,
    ) -> None:
        self._transports = transports
        self._clients = clients
        self._verifier = verifier

    def inspect(self, command: tuple[str, ...], env_names: tuple[str, ...]) -> McpServerInspection:
        """Start the server, ask, stop it, and return what it said."""
        client = self._clients.create(self._transports.open(command, env_names))
        try:
            info = client.initialize()
            tools = client.list_tools()
        finally:
            client.close()
        return McpServerInspection(info, tools)

    def check(self, entry: McpServerLock) -> tuple[str, ...]:
        """What differs between the lock and the files and the running server; empty when nothing."""
        problems = self._verifier.check_files(entry)
        if problems:
            return problems
        try:
            inspection = self.inspect(entry.command, entry.env)
        except ApplicationError as error:
            return (f"the server could not be checked: {error.message}",)
        except TransientStageError as error:
            return (f"the server could not be checked: {error}",)
        return self._verifier.check_server(entry, inspection.info, inspection.tools)
