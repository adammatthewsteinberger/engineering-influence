# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ReleaseReadinessReport."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.publishing.finding import Finding


class ReleaseReadinessReportInterface(ABC):
    """Metadata, pricing, and format decisions plus every finding about them."""

    __slots__ = ()

    @abstractmethod
    def add(self, severity: str, code: str, message: str, path: str | None = None) -> None:
        """Record a finding."""

    @property
    @abstractmethod
    def errors(self) -> list[Finding]:
        """Findings that block a release."""

    @property
    @abstractmethod
    def warnings(self) -> list[Finding]:
        """Findings that do not block a release."""

    @abstractmethod
    def as_dict(self) -> dict[str, object]:
        """Return a JSON-ready dictionary."""
