# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FrontTypesetter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from PIL import Image

    from engineering_influence.models.covers.cover_layout import CoverLayout
    from engineering_influence.models.covers.cover_style import CoverStyle


class FrontTypesetterInterface(ABC):
    """Title, subtitle, and author, centred in the front safe area."""

    __slots__ = ()

    @abstractmethod
    def typeset(
        self, layer: Image.Image, L: CoverLayout, st: CoverStyle, meta: dict[str, Any]
    ) -> None:
        """Draw onto a transparent text layer."""
