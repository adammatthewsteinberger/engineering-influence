# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ArtifactConflictError."""

from abc import ABC


class ArtifactConflictErrorInterface(ABC):
    """An artifact name that already holds different bytes."""

    __slots__ = ()
