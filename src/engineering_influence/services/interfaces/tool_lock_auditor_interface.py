# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolLockAuditor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.tool_lock import ToolLock
    from engineering_influence.models.tool_lock_finding import ToolLockFinding


class ToolLockAuditorInterface(ABC):
    """Checks locked servers against the files on disk and what they say when run."""

    __slots__ = ()

    @abstractmethod
    def audit(self, lock: ToolLock, only: Collection[str]) -> tuple[ToolLockFinding, ...]:
        """One finding per server, in name order; every server when ``only`` is empty."""
