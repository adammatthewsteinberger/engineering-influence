# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pipeline start request contract."""

from pydantic import BaseModel, ConfigDict, Field


class PipelineRequest(BaseModel):
    """Validated request naming the project whose pipeline should start."""

    model_config = ConfigDict(extra="forbid")

    project_slug: str = Field(min_length=1)
