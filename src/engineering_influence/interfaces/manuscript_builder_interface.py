# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: building an assembled book into its finished files."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from engineering_influence.models.manuscript_build import ManuscriptBuild


class ManuscriptBuilderInterface(ABC):
    """Builds, verifies and packages a book, given as the files of its project."""

    __slots__ = ()

    @abstractmethod
    def build(self, files: Mapping[str, bytes], slug: str) -> ManuscriptBuild:
        """The build of book ``slug``, whose project is ``files`` (paths such as ``books/slug.toml`` and ``src/chapter_01.md``)."""
