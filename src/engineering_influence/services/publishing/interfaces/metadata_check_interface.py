# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for MetadataCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from engineering_influence.models.publishing.release_readiness_report import (
        ReleaseReadinessReport,
    )


class MetadataCheckInterface(ABC):
    """Requires complete listing metadata and exactly seven unique keywords."""

    __slots__ = ()

    @abstractmethod
    def run(
        self,
        report: ReleaseReadinessReport,
        config: dict[str, Any],
        release: dict[str, Any],
        severity: str,
        ref: str,
    ) -> None:
        """Add findings and record description size and the metadata block."""
