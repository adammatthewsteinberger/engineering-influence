# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: running the audit gates on an assembled book."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from engineering_influence.models.manuscript_audit import ManuscriptAudit


class ManuscriptAuditorInterface(ABC):
    """Audits a book, given as the files of its project, and reports what it found."""

    __slots__ = ()

    @abstractmethod
    def audit(self, files: Mapping[str, bytes], slug: str) -> ManuscriptAudit:
        """The audit of book ``slug``, whose project is ``files`` (paths such as ``books/slug.toml`` and ``src/chapter_01.md``)."""
