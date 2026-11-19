# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Workflow-definition port."""

from abc import ABC, abstractmethod

from engineering_influence.models.project import Project


class WorkflowInterface(ABC):
    """Create an ordered workflow definition for a project."""

    @abstractmethod
    def define(self, project: Project) -> tuple[str, ...]:
        """Return ordered job kinds for the project's selected stages."""
