# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes a release bundle into a folder: the listing, the manifest, and copies of the finished files."""

import shutil
from collections.abc import Mapping
from pathlib import Path

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.interfaces.publisher_interface import PublisherInterface


class DirectoryPublisher(PublisherInterface):
    """Overwrites the files it names and leaves any other file in the folder alone.

    A source that is a symbolic link is refused, because a link could point anywhere on the machine, and a copy is
    made from the file's bytes, so the bundle is what was checked. A name that is not a plain filename is refused.
    """

    LISTING = "listing.md"
    MANIFEST = "MANIFEST.json"

    def publish(
        self, directory: Path, listing: str, manifest: str, copies: Mapping[str, Path]
    ) -> None:
        """Write the listing and manifest, then copy each source under its name."""
        for name, source in copies.items():
            if "/" in name or name in (".", "..", self.LISTING, self.MANIFEST) or not name:
                raise BookBuildError(f"a bundle file cannot be named {name!r}")
            if source.is_symlink():
                raise BookBuildError(
                    f"{source.name} is a symbolic link; the bundle copies only real files"
                )
        directory.mkdir(parents=True, exist_ok=True)
        (directory / self.LISTING).write_text(listing, encoding="utf-8")
        (directory / self.MANIFEST).write_text(manifest, encoding="utf-8")
        for name, source in copies.items():
            shutil.copyfile(source, directory / name)
