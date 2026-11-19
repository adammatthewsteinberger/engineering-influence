# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Manuscript and configuration reads from the local file system."""

from pathlib import Path

from engineering_influence.interfaces.manuscript_source_interface import ManuscriptSourceInterface


class FilesystemManuscriptSource(ManuscriptSourceInterface):
    """Reads the files of a book project from disk."""

    def exists(self, path: Path) -> bool:
        """Whether the file or directory exists."""
        return path.exists()

    def read_text(self, path: Path, errors: str = "strict") -> str:
        """Return the file's UTF-8 text; raise OSError when it cannot be read."""
        return path.read_text(encoding="utf-8", errors=errors)

    def markdown_names(self, directory: Path) -> set[str]:
        """The names of the Markdown files directly inside the directory."""
        return {path.name for path in directory.glob("*.md")}
