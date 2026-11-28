# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Starts MCP servers as child processes, each in a directory of its own."""

import os
import shutil
import tempfile
from collections.abc import Mapping
from pathlib import Path

from engineering_influence.infrastructure.process.interfaces.process_meter_interface import (
    ProcessMeterInterface,
)
from engineering_influence.infrastructure.tools.interfaces.mcp_server_sandbox_interface import (
    McpServerSandboxInterface,
)
from engineering_influence.infrastructure.tools.server_environment import ServerEnvironment
from engineering_influence.infrastructure.tools.stdio_mcp_transport import StdioMcpTransport
from engineering_influence.interfaces.mcp_transport_factory_interface import (
    McpTransportFactoryInterface,
)
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
from engineering_influence.models.tool_limits import ToolLimits


class StdioMcpTransportFactory(McpTransportFactoryInterface):
    """Makes a private working directory (mode 0700), builds the bare environment, and starts the server.

    The directory is the server's current directory, its ``HOME`` and its temporary directory, and
    it is removed when the transport is closed. If the server cannot be started, it is removed here.
    The command is wrapped by the sandbox first, so a server runs confined or not at all.
    """

    def __init__(
        self,
        limits: ToolLimits,
        environ: Mapping[str, str] | None,
        sandbox: McpServerSandboxInterface,
        meter: ProcessMeterInterface | None = None,
        sample_seconds: float = 0.5,
    ) -> None:
        self._limits = limits
        self._sandbox = sandbox
        self._environment = ServerEnvironment(os.environ if environ is None else environ)
        self._meter = meter
        self._sample_seconds = sample_seconds

    def open(self, command: tuple[str, ...], env_names: tuple[str, ...]) -> McpTransportInterface:
        """Start the server with only the named environment variables, and return its transport."""
        workdir = Path(tempfile.mkdtemp(prefix="ei-mcp-"))
        try:
            env = self._environment.build(env_names, workdir)
            confined = self._sandbox.wrap(command, workdir)
            return StdioMcpTransport(
                confined, env, self._limits, workdir, self._meter, self._sample_seconds
            )
        except BaseException:
            shutil.rmtree(workdir, ignore_errors=True)
            raise
