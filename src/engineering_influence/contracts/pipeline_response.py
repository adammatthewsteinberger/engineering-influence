"""Pipeline start response contract."""

from pydantic import BaseModel, ConfigDict


class PipelineResponse(BaseModel):
    """Stable response shared by API, MCP, CLI, and SDK adapters."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    project_slug: str
