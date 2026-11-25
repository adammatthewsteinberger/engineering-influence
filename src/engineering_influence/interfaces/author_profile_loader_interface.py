# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: where the author's own details come from."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.author_profile import AuthorProfile


class AuthorProfileLoaderInterface(ABC):
    """Reads an author profile from a file the person named, strictly."""

    __slots__ = ()

    @abstractmethod
    def load(self, path: Path) -> AuthorProfile | None:
        """The profile, None when there is no such file, or an ApplicationError (AUTHOR_PROFILE_INVALID) when the file is not one."""
