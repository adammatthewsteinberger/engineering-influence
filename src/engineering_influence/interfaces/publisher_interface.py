# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for writing a finished release bundle to a folder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path


class PublisherInterface(ABC):
    """Write a release bundle: a listing, a manifest, and copies of finished files."""

    __slots__ = ()

    @abstractmethod
    def publish(
        self, directory: Path, listing: str, manifest: str, copies: Mapping[str, Path]
    ) -> None:
        """Write ``listing.md`` and ``MANIFEST.json`` into ``directory`` and copy each source under its name."""
