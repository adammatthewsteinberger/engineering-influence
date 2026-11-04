# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Controller port for project operations."""

from abc import ABC, abstractmethod

from engineering_influence.contracts.pipeline_response import PipelineResponse
from engineering_influence.contracts.project_request import ProjectRequest


class ProjectControllerInterface(ABC):
    """Transport-neutral project controller contract."""

    @abstractmethod
    def start(self, request: ProjectRequest) -> PipelineResponse:
        """Create the project and enqueue its first stage."""
