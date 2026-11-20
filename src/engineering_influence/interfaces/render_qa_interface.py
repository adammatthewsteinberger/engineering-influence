# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for rendering a PDF's pages for visual QA."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.qa.render_report import RenderReport


class RenderQaInterface(ABC):
    """Render every page of a PDF and report what was found."""

    __slots__ = ()

    @abstractmethod
    def render(self, pdf: Path, output: Path, *, dpi: int = 90) -> RenderReport:
        """Render the pages into output and return the report."""
