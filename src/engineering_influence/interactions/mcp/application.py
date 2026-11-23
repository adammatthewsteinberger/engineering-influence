# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Model Context Protocol interaction over the shared controller."""

from typing import Any

from engineering_influence.contracts.brief.v1.book_brief_v1 import BookBriefV1
from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.contracts.run.v1.run_summary_v1 import RunSummaryV1
from engineering_influence.controllers.interfaces.project_controller_interface import (
    ProjectControllerInterface,
)
from engineering_influence.interactions.mcp.interfaces.application_interface import (
    McpApplicationInterface,
)
from engineering_influence.services.interfaces.create_run_interface import CreateRunInterface
from engineering_influence.services.interfaces.run_management_interface import (
    RunManagementInterface,
)


class McpApplication(McpApplicationInterface):
    """Expose pipeline tools through the official MCP SDK's `MCPServer` (mcp 2.x)."""

    def __init__(
        self,
        controller: ProjectControllerInterface,
        creator: CreateRunInterface | None = None,
        manager: RunManagementInterface | None = None,
    ) -> None:
        self._controller = controller
        self._creator = creator
        self._manager = manager

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

        if self._creator is not None:
            creator = self._creator

            @server.tool()
            def create_run(brief: dict[str, Any]) -> dict[str, Any]:
                """Start a book run from a brief (the brief contract v1); returns the new run."""
                value = BookBriefV1.model_validate(brief).to_model()
                return RunSummaryV1.from_run(creator.create(value), []).model_dump(mode="json")

        if self._manager is not None:
            manager = self._manager

            @server.tool()
            def list_runs() -> list[dict[str, Any]]:
                """Every saved book run, as run summaries."""
                return [
                    RunSummaryV1.from_run(run, []).model_dump(mode="json") for run in manager.runs()
                ]

            @server.tool()
            def resume_run(run_id: str) -> dict[str, Any]:
                """Un-park a parked run and queue its current stage."""
                return RunSummaryV1.from_run(manager.resume(run_id), []).model_dump(mode="json")

            @server.tool()
            def cancel_run(run_id: str) -> dict[str, Any]:
                """Stop a run for good."""
                return RunSummaryV1.from_run(manager.cancel(run_id), []).model_dump(mode="json")

        return server

    async def run_stdio(self) -> None:
        """Run the server over MCP stdio transport."""
        server = self.build()
        await server.run_stdio_async()
