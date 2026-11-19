# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Directory conventions of a publishing project."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectLayout:
    """Where a project keeps book configs, build products, and finished outputs.

    The directory names default to books, build, and output; a project can rename them in its
    engineering-influence.toml.
    """

    root: Path
    books_dir: str = "books"
    output_dir: str = "output"
    build_dir: str = "build"

    @property
    def books(self) -> Path:
        """Per-book TOML configuration files."""
        return self.root / self.books_dir

    @property
    def build(self) -> Path:
        """Scratch directory for generated sources and logs."""
        return self.root / self.build_dir

    @property
    def output(self) -> Path:
        """Finished PDFs and EPUBs."""
        return self.root / self.output_dir
