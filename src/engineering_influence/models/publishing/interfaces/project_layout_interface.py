# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ProjectLayout."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class ProjectLayoutInterface(ABC):
    """Where a project keeps book configs, build products, and finished outputs."""

    __slots__ = ()

    @property
    @abstractmethod
    def books(self) -> Path:
        """Per-book TOML configuration files."""

    @property
    @abstractmethod
    def build(self) -> Path:
        """Scratch directory for generated sources and logs."""

    @property
    @abstractmethod
    def output(self) -> Path:
        """Finished PDFs and EPUBs."""
