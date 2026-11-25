# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ResearchCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from engineering_influence.models.publishing.path_relativizer import PathRelativizer
    from engineering_influence.models.publishing.release_readiness_report import (
        ReleaseReadinessReport,
    )


class ResearchCheckInterface(ABC):
    """Counts words and URLs in the configured research files."""

    __slots__ = ()

    @abstractmethod
    def run(
        self,
        report: ReleaseReadinessReport,
        source: Path,
        release: dict[str, Any],
        severity: str,
        relativizer: PathRelativizer,
    ) -> None:
        """Add findings and record research size."""
