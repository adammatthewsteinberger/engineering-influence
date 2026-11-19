# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Model Context Protocol interaction over the shared controller."""

from typing import Any

from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.controllers.interfaces.project_controller_interface import (
    ProjectControllerInterface,
)


class McpApplication:
    """Expose pipeline tools through the official MCP SDK's `MCPServer` (mcp 2.x)."""

    def __init__(self, controller: ProjectControllerInterface) -> None:
        self._controller = controller

    def build(self) -> Any:
        """Build a server with a typed `start_pipeline` tool."""
        from mcp.server.mcpserver import MCPServer

        server = MCPServer(
            name="engineering-influence",
            instructions="Start evidence-bounded content pipelines.",
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
