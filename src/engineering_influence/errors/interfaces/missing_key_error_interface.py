# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for MissingKeyError."""

from __future__ import annotations

from abc import ABC


class MissingKeyErrorInterface(ABC, Exception):
    """A key an object store was asked for is not in the bucket."""

    __slots__ = ()
