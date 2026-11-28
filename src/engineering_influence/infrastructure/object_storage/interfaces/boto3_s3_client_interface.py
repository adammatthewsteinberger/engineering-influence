# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for the three S3 calls the object store makes. A boto3 client sits behind it; a test fake can sit behind it too."""

from abc import ABC, abstractmethod


class Boto3S3ClientInterface(ABC):
    """put, get and list, the calls an S3-compatible service must answer."""

    __slots__ = ()

    @abstractmethod
    def put_object(self, bucket: str, key: str, body: bytes) -> None:
        """Store the object under the key, replacing any object already there."""

    @abstractmethod
    def get_object(self, bucket: str, key: str) -> bytes:
        """The object's bytes; raises MissingKeyError when the key is not there."""

    @abstractmethod
    def list_keys(self, bucket: str, prefix: str) -> list[str]:
        """Every key under the prefix, in any order."""
