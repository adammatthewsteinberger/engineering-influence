# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ArtifactAddress."""

from abc import ABC, abstractmethod


class ArtifactAddressInterface(ABC):
    """Where an artifact lives: the run that made it and its name within that run."""

    __slots__ = ()

    @abstractmethod
    def relative_path(self) -> str:
        """The address as ``run_id/name``, with forward slashes."""
