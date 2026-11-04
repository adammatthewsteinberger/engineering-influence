# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Model Context Protocol interaction over the shared controller."""

from typing import Any

from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.interfaces.ledger_port import LedgerPort
from engineering_influence.interfaces.queue_port import QueuePort
from engineering_influence.services.start_pipeline import StartPipeline


class McpApplication:
    """Expose pipeline tools through the official MCP FastMCP server."""

    def __init__(self, ledger: LedgerPort, queue: QueuePort) -> None:
        self._controller = ProjectController(StartPipeline(ledger, queue))

    def build(self) -> Any:
        """Build a server with a typed `start_pipeline` tool."""
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(
            name="engineering-influence",
            instructions="Start and inspect evidence-bounded content pipelines.",
        )

        @server.tool()
        def start_pipeline(
            slug: str,
            title: str,
            postulates: list[str],
            stages: list[str],
        ) -> dict[str, str]:
            """Create a project and enqueue its first selected stage."""
            request = ProjectRequest(
                slug=slug,
                title=title,
                postulates=tuple(postulates),
                stages=tuple(stages),
            )
            return self._controller.start(request).model_dump()

        return server

    async def run_stdio(self) -> None:
        """Run the server over MCP stdio transport."""
        server = self.build()
        await server.run_stdio_async()
