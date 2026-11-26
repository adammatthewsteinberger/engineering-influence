# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SceneRevision."""

from __future__ import annotations

from abc import ABC, abstractmethod


class SceneRevisionInterface(ABC):
    """What the revision stage did to one scene."""

    __slots__ = ()

    @abstractmethod
    def status(self) -> str:
        """`draft kept` when the scene's revision was not used, otherwise `revised`."""
