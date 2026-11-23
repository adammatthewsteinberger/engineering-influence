# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes a project's files into a new folder, all or nothing."""

import os
import shutil
import tempfile
from collections.abc import Mapping
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.project_files_writer_interface import (
    ProjectFilesWriterInterface,
)


class DirectoryProjectFilesWriter(ProjectFilesWriterInterface):
    """Builds the tree in a private folder beside the target and moves it into place, so a failure leaves nothing behind.

    The target may be missing or an empty folder; anything else (a file, a link, a folder with something in it) is
    refused, so nothing of the author's is overwritten. Each file is created new and never through a link. A path that
    is absolute, climbs, is empty or holds a backslash is refused before anything is written.
    """

    def write(self, root: Path, files: Mapping[str, bytes]) -> None:
        """Write every file under ``root`` or none of them."""
        self._check_target(root)
        for name in files:
            self._check_name(name)
        root.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".ei-export-", dir=root.parent))
        try:
            for name, data in files.items():
                path = staging / name
                path.parent.mkdir(parents=True, exist_ok=True)
                descriptor = os.open(
                    path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644
                )
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(data)
            staging.replace(root)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    @staticmethod
    def _check_target(root: Path) -> None:
        if root.is_symlink() or (root.exists() and (not root.is_dir() or any(root.iterdir()))):
            raise ApplicationError(
                code="EXPORT_TARGET_NOT_EMPTY",
                message=f"{root} already exists and is not an empty folder; export to a new one",
                http_status=409,
            )

    @staticmethod
    def _check_name(name: str) -> None:
        # An absolute path and an empty name both split into a first part that is empty.
        if "\\" in name or any(part in ("", ".", "..") for part in name.split("/")):
            raise ValueError(f"the path {name!r} is not a relative path inside the folder")
