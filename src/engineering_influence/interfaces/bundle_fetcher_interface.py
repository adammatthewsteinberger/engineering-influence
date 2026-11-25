# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: downloading the bytes of a file from an https address."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BundleFetcherInterface(ABC):
    """Downloads a file and says nothing about what is in it."""

    __slots__ = ()

    @abstractmethod
    def fetch(self, url: str, max_bytes: int) -> bytes:
        """The file's bytes, at most ``max_bytes`` of them, or an ApplicationError (BUNDLE_*) saying why not."""
