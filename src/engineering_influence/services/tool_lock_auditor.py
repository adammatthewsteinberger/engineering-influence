# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Checks every locked server and says which still match what was approved."""

from collections.abc import Collection

from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.models.tool_lock_finding import ToolLockFinding
from engineering_influence.services.interfaces.mcp_server_probe_interface import (
    McpServerProbeInterface,
)
from engineering_influence.services.interfaces.tool_lock_auditor_interface import (
    ToolLockAuditorInterface,
)


class ToolLockAuditor(ToolLockAuditorInterface):
    """One server at a time, each stopped before the next is started.

    A name that is not in the lock is an error rather than a skipped check, so a misspelt name
    cannot look like a pass.
    """

    def __init__(self, probe: McpServerProbeInterface) -> None:
        self._probe = probe

    def audit(self, lock: ToolLock, only: Collection[str]) -> tuple[ToolLockFinding, ...]:
        """One finding per server, in name order; every server when ``only`` is empty."""
        unknown = sorted(set(only) - set(lock.names()))
        if unknown:
            raise ValueError(f"no server named {unknown[0]!r} is locked")
        wanted = set(only)
        servers = sorted(lock.servers, key=lambda server: server.name)
        return tuple(
            ToolLockFinding(server.name, self._probe.check(server))
            for server in servers
            if not wanted or server.name in wanted
        )
