# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Project creation request contract."""

from pydantic import BaseModel, ConfigDict, Field

from engineering_influence.contracts.interfaces.project_request_interface import (
    ProjectRequestInterface,
)


class ProjectRequest(ProjectRequestInterface, BaseModel):
    """Validated project data accepted by an interaction."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    postulates: tuple[str, ...] = Field(min_length=1)
    stages: tuple[str, ...] = Field(min_length=1)
