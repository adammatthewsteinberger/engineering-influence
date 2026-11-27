# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for a bucketed object store: put, get and list keys, with no knowledge of runs or artifacts."""

from abc import ABC, abstractmethod


class S3ObjectStoreInterface(ABC):
    """The three operations the artifact store needs from an S3-compatible service."""

    __slots__ = ()

    @abstractmethod
    def put(self, bucket: str, key: str, body: bytes) -> None:
        """Store the object, replacing any object already under the key."""

    @abstractmethod
    def get(self, bucket: str, key: str) -> bytes | None:
        """The object's bytes, or None when the key is not there."""

    @abstractmethod
    def keys(self, bucket: str, prefix: str) -> list[str]:
        """Every key under the prefix, sorted."""
