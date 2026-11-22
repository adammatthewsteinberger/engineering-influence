# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolLockEditor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.tool_lock import ToolLock
    from engineering_influence.models.tool_lock_addition import ToolLockAddition


class ToolLockEditorInterface(ABC):
    """Turns a command a person names into a reviewed entry in the lock."""

    __slots__ = ()

    @abstractmethod
    def add(
        self,
        lock: ToolLock,
        name: str,
        argv: tuple[str, ...],
        env_names: tuple[str, ...],
        replace: bool,
    ) -> ToolLockAddition:
        """Run the server once, record what it is, and return the lock with it added."""
