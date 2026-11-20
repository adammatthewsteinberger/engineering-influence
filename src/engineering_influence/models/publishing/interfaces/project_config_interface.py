# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ProjectConfig."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.publishing.project_config import ProjectConfig
    from engineering_influence.models.publishing.project_layout import ProjectLayout


class ProjectConfigInterface(ABC):
    """The consumer configuration of a book project."""

    __slots__ = ()

    @classmethod
    @abstractmethod
    def load(cls, root: Path) -> ProjectConfig:
        """Read root/engineering-influence.toml when it exists."""

    @abstractmethod
    def layout(self) -> ProjectLayout:
        """The directory layout this configuration describes."""

    @abstractmethod
    def font_dirs(self) -> list[Path]:
        """Where the project keeps cover fonts."""

    @abstractmethod
    def activate(self) -> None:
        """Make the project importable, so a plugin named `module:Class` can be found."""
