# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PublishingController."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from engineering_influence.models.publishing.project_layout import ProjectLayout


class PublishingControllerInterface(ABC):
    """One entry point per publishing operation, shared by every transport."""

    __slots__ = ()

    @property
    @abstractmethod
    def layout(self) -> ProjectLayout:
        """The project's directory layout."""

    @abstractmethod
    def audit(self, slug: str, *, strict_release: bool = False) -> tuple[dict[str, Any], bool, str]:
        """Return (both reports as dictionaries, whether the manuscript passes, text)."""

    @abstractmethod
    def build(
        self, slug: str, *, hardcover: bool = False, tex_only: bool = False, verify: bool = True
    ) -> str:
        """Build the interior PDF (or only its LaTeX) and verify the PDF."""

    @abstractmethod
    def epub(self, slug: str, *, tex_only: bool = False, verify: bool = True) -> str:
        """Build the EPUB (or only its LaTeX) and verify the EPUB."""

    @abstractmethod
    def covers(self, slug: str, *, preview: bool = False, hardcover_pdf: Path | None = None) -> str:
        """Build and verify every cover file."""

    @abstractmethod
    def qa(
        self, pdf: Path, *, output: Path | None = None, dpi: int = 90
    ) -> tuple[dict[str, Any], bool]:
        """Render every page of a PDF; return (the report, whether no blank run is overlong)."""

    @abstractmethod
    def publish(
        self,
        slug: str,
        *,
        dpi: int = 90,
        audit_only: bool = False,
        no_render: bool = False,
        report_path: Path | None = None,
        strict_release: bool = False,
    ) -> tuple[dict[str, Any], bool]:
        """Run the complete acceptance pipeline for one book."""

    @abstractmethod
    def book_slugs(self) -> list[str]:
        """Every book the project configures."""
