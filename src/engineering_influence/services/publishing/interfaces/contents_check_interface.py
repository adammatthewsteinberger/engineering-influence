# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ContentsCheck."""

from abc import ABC, abstractmethod


class ContentsCheckInterface(ABC):
    """Compares Contents entries with the folios printed on the pages themselves."""

    __slots__ = ()

    @abstractmethod
    def run(
        self, texts: list[str], folios: list[str | None], title: str
    ) -> tuple[list[str], int | None]:
        """Return (problems, entries checked); entries is None when no Contents page exists."""
