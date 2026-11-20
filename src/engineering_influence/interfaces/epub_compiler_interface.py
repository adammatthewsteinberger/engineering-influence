# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for converting ebook LaTeX to an EPUB."""

from abc import ABC, abstractmethod
from pathlib import Path


class EpubCompilerInterface(ABC):
    """Run the EPUB conversion toolchain in a working directory."""

    __slots__ = ()

    @abstractmethod
    def compile(self, workdir: Path, tex_name: str) -> tuple[int, str]:
        """Run the conversion; return (exit status, captured stdout and stderr)."""
