# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Composition root for the publishing controller."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.controllers.publishing_controller import PublishingController


class PublishingControllerFactoryInterface(ABC):
    """Build a fully wired publishing controller for a project root."""

    __slots__ = ()

    @abstractmethod
    def create(self, root: Path) -> PublishingController:
        """Load the project at ``root`` and wire its collaborators."""
