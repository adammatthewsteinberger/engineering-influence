"""SHA-256 of a file."""

import hashlib
from pathlib import Path


class FileDigest:
    """Hashes in 1 MiB blocks so large PDFs never load whole."""

    def sha256(self, path: Path) -> str:
        """The hex digest of the file's bytes."""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
