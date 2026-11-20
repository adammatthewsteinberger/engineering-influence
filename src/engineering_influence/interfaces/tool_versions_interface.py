# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for reading the versions of external tools."""

from abc import ABC, abstractmethod


class ToolVersionsInterface(ABC):
    """Report which tools a build used and their versions."""

    __slots__ = ()

    @abstractmethod
    def of(self, command: str) -> str | None:
        """The version banner of one tool, or None when it is not installed."""

    @abstractmethod
    def environment(self) -> dict[str, str | None]:
        """Python and the toolchain the pipeline depends on."""
