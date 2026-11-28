# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Artifact store held in memory, for local demonstrations and tests."""

import hashlib

from engineering_influence.errors.artifact_conflict_error import ArtifactConflictError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.models.artifact_address import ArtifactAddress


class InMemoryArtifactStore(ArtifactStoreInterface):
    """Keeps each run's artifacts in a dictionary."""

    def __init__(self) -> None:
        """Start with no artifacts."""
        self._files: dict[str, bytes] = {}

    def put(self, run_id: str, name: str, data: bytes) -> str:
        """Store the bytes under the run's name, refusing to replace different bytes already there, and return their SHA-256 digest."""
        address = ArtifactAddress(run_id, name).relative_path()
        existing = self._files.get(address)
        if existing is not None and existing != data:
            raise ArtifactConflictError(f"{address} already holds different bytes")
        self._files[address] = data
        return hashlib.sha256(data).hexdigest()

    def get(self, run_id: str, name: str) -> bytes | None:
        """The bytes stored under the run's name, or None when there are none."""
        return self._files.get(ArtifactAddress(run_id, name).relative_path())

    def names(self, run_id: str) -> list[str]:
        """The names of every artifact stored for the run, relative to the run's folder, sorted."""
        prefix = ArtifactAddress(run_id, "x").relative_path()[:-1]
        return sorted(path[len(prefix) :] for path in self._files if path.startswith(prefix))
