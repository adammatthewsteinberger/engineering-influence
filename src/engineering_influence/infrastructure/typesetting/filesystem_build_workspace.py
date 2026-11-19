# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The files a book build writes, on the local file system."""

import shutil
from pathlib import Path

from engineering_influence.interfaces.build_workspace_interface import BuildWorkspaceInterface


class FilesystemBuildWorkspace(BuildWorkspaceInterface):
    """Prepares build directories and delivers finished PDFs."""

    def prepare(self, workdir: Path, assets: Path, hardcover: bool) -> None:
        """Create the directory and copy the class files and fonts into it."""
        workdir.mkdir(parents=True, exist_ok=True)
        if hardcover:
            shutil.copy(assets / "fine-book-hardcover.cls", workdir / "fine-book-hardcover.cls")
        shutil.copy(assets / "fine-book.cls", workdir / "fine-book.cls")
        # The interior fonts travel with the package, so the PDF does not depend on which TeX
        # distribution built it.
        shutil.copytree(assets / "fonts", workdir / "fonts", dirs_exist_ok=True)

    def write_text(self, path: Path, text: str) -> None:
        """Write UTF-8 text."""
        path.write_text(text, encoding="utf-8")

    def deliver(self, built: Path, destination: Path) -> None:
        """Copy the built file to its destination, creating the destination's folder."""
        destination.parent.mkdir(exist_ok=True)
        shutil.copy(built, destination)
