# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ReleaseAuditor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.publishing.release_readiness_report import (
        ReleaseReadinessReport,
    )


class ReleaseAuditorInterface(ABC):
    """Proves a release has the decisions that used to live in chat or memory."""

    __slots__ = ()

    @abstractmethod
    def audit(
        self, config_path: Path, *, pdf: Path | None = None, strict: bool = False
    ) -> ReleaseReadinessReport:
        """Return the readiness report for one book config."""
