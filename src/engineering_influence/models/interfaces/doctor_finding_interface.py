# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for DoctorFinding."""

from abc import ABC, abstractmethod


class DoctorFindingInterface(ABC):
    """One thing the doctor checked, and whether it held."""

    __slots__ = ()

    @abstractmethod
    def line(self) -> str:
        """The finding as one line of output."""
