# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for compiling a LaTeX document to a PDF."""

from abc import ABC, abstractmethod
from pathlib import Path


class LatexCompilerInterface(ABC):
    """Run the LaTeX toolchain in a working directory."""

    __slots__ = ()

    @abstractmethod
    def compile(self, workdir: Path, tex_name: str, source_date_epoch: int) -> tuple[int, str]:
        """Run the build; return (exit status, captured stdout)."""
