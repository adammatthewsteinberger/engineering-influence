# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Model Context Protocol interaction over the shared controller."""

import base64
from typing import Any, ClassVar

from engineering_influence.contracts.brief.v1.book_brief_v1 import BookBriefV1
from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.contracts.run.v1.run_summary_v1 import RunSummaryV1
from engineering_influence.controllers.interfaces.project_controller_interface import (
    ProjectControllerInterface,
)
from engineering_influence.controllers.interfaces.run_controller_interface import (
    RunControllerInterface,
)
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.mcp.interfaces.application_interface import (
    McpApplicationInterface,
)
from engineering_influence.services.interfaces.create_run_interface import CreateRunInterface
from engineering_influence.services.interfaces.run_management_interface import (
    RunManagementInterface,
)


class McpApplication(McpApplicationInterface):
    """Expose pipeline tools through the official MCP SDK's `MCPServer` (mcp 2.x).

    With a run reader it also offers ``get_run`` and ``read_artifact``, so an agent that started a run can see where it
    is and read what it made. An artifact is returned as text when it is UTF-8 and as base64 when it is not, and one
    larger than ``MAX_ARTIFACT_BYTES`` is refused (``ARTIFACT_TOO_LARGE``) with the address that downloads any size.

    ``grant_run`` and ``deny_run`` spend or withhold the person's money, so a server built with ``allow_spend=False``
    does not offer them: an agent can start a run and read it, but only a person can give it more budget.
    """

    MAX_ARTIFACT_BYTES: ClassVar[int] = 1_048_576

    def __init__(
        self,
        controller: ProjectControllerInterface,
        creator: CreateRunInterface | None = None,
        manager: RunManagementInterface | None = None,
        reader: RunControllerInterface | None = None,
        allow_spend: bool = True,
    ) -> None:
        self._controller = controller
        self._creator = creator
        self._manager = manager
        self._reader = reader
        self._allow_spend = allow_spend

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

            if self._allow_spend:

                @server.tool()
                def grant_run(run_id: str, micro_usd: int | None = None) -> dict[str, Any]:
                    """Give a run more budget and continue it: the amount it asked for, or micro_usd for a parked run."""
                    return RunSummaryV1.from_run(manager.grant(run_id, micro_usd), []).model_dump(
                        mode="json"
                    )

                @server.tool()
                def deny_run(run_id: str) -> dict[str, Any]:
                    """Refuse a run's request for more budget; the run parks."""
                    return RunSummaryV1.from_run(manager.deny(run_id), []).model_dump(mode="json")

        if self._reader is not None:
            reader = self._reader
            limit = self.MAX_ARTIFACT_BYTES

            @server.tool()
            def get_run(run_id: str) -> dict[str, Any]:
                """A run's summary: its status, stage, budget and the names of the artifacts it has stored."""
                return reader.summary(run_id).model_dump(mode="json")

            @server.tool()
            def read_artifact(run_id: str, name: str) -> dict[str, Any]:
                """One stored artifact of a run, as text when it is UTF-8 and as base64 when it is not."""
                data = reader.artifact(run_id, name)
                if len(data) > limit:
                    raise ApplicationError(
                        code="ARTIFACT_TOO_LARGE",
                        message=f"artifact {name!r} is {len(data)} bytes; this tool returns at most {limit}. "
                        f"Download it from GET /v1/runs/{run_id}/artifacts/{name}",
                        http_status=413,
                    )
                try:
                    encoding, content = "utf-8", data.decode("utf-8")
                except UnicodeDecodeError:
                    encoding, content = "base64", base64.b64encode(data).decode("ascii")
                return {"name": name, "bytes": len(data), "encoding": encoding, "content": content}

        return server

    async def run_stdio(self) -> None:
        """Run the server over MCP stdio transport."""
        server = self.build()
        await server.run_stdio_async()
