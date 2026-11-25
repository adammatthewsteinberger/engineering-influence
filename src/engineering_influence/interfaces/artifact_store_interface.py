# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Artifact store port."""

from abc import ABC, abstractmethod


class ArtifactStoreInterface(ABC):
    """Keep the files a run produces, write-once, so a resumed run finds them unchanged."""

    __slots__ = ()

    @abstractmethod
    def put(self, run_id: str, name: str, data: bytes) -> str:
        """Store the bytes and return their SHA-256; the same bytes again are accepted, different bytes are not."""

    @abstractmethod
    def get(self, run_id: str, name: str) -> bytes | None:
        """The stored bytes, or None if the run never stored that name."""

    @abstractmethod
    def names(self, run_id: str) -> list[str]:
        """Every name stored for a run, sorted."""
