# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pipeline-start service contract."""

from abc import ABC, abstractmethod

from engineering_influence.domain.project import Project


class StartPipelineInterface(ABC):
    """Starts a project through the durable application ports."""

    @abstractmethod
    def start(self, project: Project) -> str:
        """Record the start and enqueue the first stage."""
        raise NotImplementedError
