# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pipeline start response contract."""

from pydantic import BaseModel, ConfigDict

from engineering_influence.contracts.interfaces.pipeline_response_interface import (
    PipelineResponseInterface,
)


class PipelineResponse(PipelineResponseInterface, BaseModel):
    """Stable response shared by API, MCP, CLI, and SDK adapters."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    project_slug: str
