# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Lays the files of a project out below a folder, the same way for an audit and for a build."""

from collections.abc import Mapping
from pathlib import Path

from engineering_influence.interfaces.scratch_project_interface import ScratchProjectInterface


class ScratchProject(ScratchProjectInterface):
    """A file whose path would leave the folder is refused before anything is written for it."""

    @staticmethod
    def write(root: Path, files: Mapping[str, bytes]) -> None:
        for name, data in files.items():
            target = (root / name).resolve()
            if not target.is_relative_to(root) or target == root:
                raise ValueError(f"the file {name!r} would leave the project")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
