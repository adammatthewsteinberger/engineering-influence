# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SHA-256 of a file on disk."""

import hashlib
from pathlib import Path

from engineering_influence.interfaces.file_hasher_interface import FileHasherInterface


class Sha256FileHasher(FileHasherInterface):
    """Reads a regular file in blocks, following symlinks to what they point at.

    A symlink is hashed by what it points at, so a link that is repointed at other code gives a
    different hash. Anything that is not a readable regular file (a directory, a missing path, a
    permission error) gives ``None``, so a caller never has to tell those apart from a mismatch.
    """

    BLOCK = 1 << 20

    def digest(self, path: str) -> str | None:
        """The SHA-256 of the file's contents in lowercase hex, or None if it is not a readable regular file."""
        target = Path(path)
        try:
            if not target.is_file():
                return None
            hasher = hashlib.sha256()
            with target.open("rb") as handle:
                while block := handle.read(self.BLOCK):
                    hasher.update(block)
        except OSError:
            return None
        return hasher.hexdigest()
