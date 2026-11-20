# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The project aggregate."""

from dataclasses import dataclass, field

from engineering_influence.models.governing_postulates import GoverningPostulates
from engineering_influence.models.interfaces.project_interface import ProjectInterface
from engineering_influence.models.limits_on_means import LimitsOnMeans
from engineering_influence.models.pipeline_stage import PipelineStage


@dataclass(frozen=True, slots=True)
class Project(ProjectInterface):
    """A project with neutral governing postulates and fixed means limits."""

    slug: str
    title: str
    postulates: GoverningPostulates
    stages: tuple[PipelineStage, ...]
    limits: LimitsOnMeans = field(default_factory=LimitsOnMeans)

    def __post_init__(self) -> None:
        if not self.slug.strip() or not self.title.strip():
            raise ValueError("project slug and title are required")
        if not self.stages:
            raise ValueError("project requires at least one pipeline stage")
