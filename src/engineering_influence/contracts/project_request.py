"""Project creation request contract."""

from pydantic import BaseModel, ConfigDict, Field


class ProjectRequest(BaseModel):
    """Validated project data accepted by an interaction."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    postulates: tuple[str, ...] = Field(min_length=1)
    stages: tuple[str, ...] = Field(min_length=1)
