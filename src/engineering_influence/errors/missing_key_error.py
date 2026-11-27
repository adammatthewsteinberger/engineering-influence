# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Raised when an object store is asked for a key that is not there."""

from engineering_influence.errors.interfaces.missing_key_error_interface import (
    MissingKeyErrorInterface,
)


class MissingKeyError(MissingKeyErrorInterface):
    """The key is not in the bucket; the object store reads it as None."""
