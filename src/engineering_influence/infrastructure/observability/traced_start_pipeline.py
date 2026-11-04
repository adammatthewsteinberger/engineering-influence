# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tracing decorator for the pipeline-start service."""

from vibey_bootstrap.tracing.decorators import traced

from engineering_influence.domain.project import Project
from engineering_influence.services.interfaces.start_pipeline_interface import (
    StartPipelineInterface,
)


class TracedStartPipeline(StartPipelineInterface):
    """Record latency and errors for every start, without logging the project."""

    def __init__(self, inner: StartPipelineInterface) -> None:
        self._inner = inner

    @traced(operation="service.start_pipeline", sensitive_args=("project",))
    def start(self, project: Project) -> str:
        """Delegate to the wrapped service."""
        return self._inner.start(project)
