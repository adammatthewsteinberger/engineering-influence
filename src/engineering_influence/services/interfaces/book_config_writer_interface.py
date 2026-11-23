# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BookConfigWriter."""

from abc import ABC, abstractmethod


class BookConfigWriterInterface(ABC):
    """Writes the TOML config of an assembled book."""

    __slots__ = ()

    @abstractmethod
    def write(self, kind: str, title: str, trim_size: str | None, chapters: tuple[str, ...]) -> str:
        """The config text: the kind, the title, the source folder and one part holding the chapter files."""
