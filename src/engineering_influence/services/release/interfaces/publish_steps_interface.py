# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PublishSteps."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.services.release.publish_steps import Step


class PublishStepsInterface(ABC):
    """Each action builds one artifact set and raises BookBuildError if its checks fail."""

    __slots__ = ()

    @abstractmethod
    def plan(self, slug: str, *, hardcover: bool, strict: bool = False) -> list[Step]:
        """The ordered steps: interior, optional hardcover interior, covers, then the EPUB."""

    @abstractmethod
    def pdf(self, slug: str) -> str:
        """Build and verify the paperback interior."""

    @abstractmethod
    def hardcover(self, slug: str) -> str:
        """Build and verify the compact hardcover interior."""

    @abstractmethod
    def covers(self, slug: str, *, hardcover: bool) -> str:
        """Build and verify every cover file, with previews."""

    @abstractmethod
    def epub(self, slug: str, *, strict: bool = False) -> str:
        """Build and verify the EPUB; a strict release also requires epubcheck to run."""
