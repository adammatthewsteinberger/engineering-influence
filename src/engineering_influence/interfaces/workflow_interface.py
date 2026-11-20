# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Workflow-definition port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.project import Project


class WorkflowInterface(ABC):
    """Create an ordered workflow definition for a project."""

    __slots__ = ()

    @abstractmethod
    def define(self, project: Project) -> tuple[str, ...]:
        """Return ordered job kinds for the project's selected stages."""
