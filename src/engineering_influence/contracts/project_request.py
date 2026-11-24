# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Project creation request contract."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from engineering_influence.contracts.interfaces.project_request_interface import (
    ProjectRequestInterface,
)
from engineering_influence.models.pipeline_stage import PipelineStage


class ProjectRequest(ProjectRequestInterface, BaseModel):
    """Validated project data accepted by an interaction."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    postulates: tuple[str, ...] = Field(min_length=1)
    stages: tuple[str, ...] = Field(min_length=1)

    @field_validator("stages")
    @classmethod
    def _known_stages(cls, stages: tuple[str, ...]) -> tuple[str, ...]:
        """Refuse a stage that does not exist here, where every interface validates, not later as a crash."""
        known = [stage.value for stage in PipelineStage]
        for stage in stages:
            if stage not in known:
                raise ValueError(f"unknown stage {stage!r}: use one of {', '.join(known)}")
        return stages
