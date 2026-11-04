"""Workflow-definition port."""

from abc import ABC, abstractmethod

from engineering_influence.domain.project import Project


class WorkflowPort(ABC):
    """Create an ordered workflow definition for a project."""

    @abstractmethod
    def define(self, project: Project) -> tuple[str, ...]:
        """Return ordered job kinds for the project's selected stages."""
