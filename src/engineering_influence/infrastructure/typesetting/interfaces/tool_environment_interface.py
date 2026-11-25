# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolEnvironment."""

from abc import ABC, abstractmethod


class ToolEnvironmentInterface(ABC):
    """Model-written text reaches TeX, so the build tools must not inherit secrets."""

    __slots__ = ()

    @abstractmethod
    def build(self, source_date_epoch: int | None = None) -> dict[str, str]:
        """The allow-listed variables, plus SOURCE_DATE_EPOCH when one is given."""
