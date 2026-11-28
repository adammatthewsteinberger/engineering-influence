# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RevisionReportWriter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.scene_revision import SceneRevision
    from engineering_influence.models.shooting_lock import ShootingLock


class RevisionReportWriterInterface(ABC):
    """Writes the revision log and the source mapping of a locked screenplay."""

    __slots__ = ()

    @abstractmethod
    def revision_log(self, lock: ShootingLock, scenes: tuple[SceneRevision, ...]) -> str:
        """A table of every locked scene in script order: its number, its card, whether its revision was used, and the
        word counts. Each scene the lock keeps must have an entry in `scenes`."""

    @abstractmethod
    def source_mapping(self, lock: ShootingLock, scenes: tuple[SceneRevision, ...]) -> str:
        """A table of every locked scene in script order: its number, its card, its beat, and the source files it cites."""
