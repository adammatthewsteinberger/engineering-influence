# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ShootingScriptRenderer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.shooting_lock import ShootingLock


class ShootingScriptRendererInterface(ABC):
    """Writes a Fountain script with its scene numbers printed."""

    __slots__ = ()

    @abstractmethod
    def render(self, script: str, cards: tuple[int, ...], lock: ShootingLock) -> str:
        """The script with each scene's number in its heading, and each omitted scene in its place. `cards` gives each
        scene's card in script order; the script must have one scene for each card."""
