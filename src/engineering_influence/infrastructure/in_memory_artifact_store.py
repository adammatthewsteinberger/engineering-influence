# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Artifact store held in memory, for local demonstrations and tests."""

import hashlib

from engineering_influence.errors.artifact_conflict_error import ArtifactConflictError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.models.artifact_address import ArtifactAddress


class InMemoryArtifactStore(ArtifactStoreInterface):
    """Keeps each run's artifacts in a dictionary."""

    def __init__(self) -> None:
        self._files: dict[str, bytes] = {}

    def put(self, run_id: str, name: str, data: bytes) -> str:
        address = ArtifactAddress(run_id, name).relative_path()
        existing = self._files.get(address)
        if existing is not None and existing != data:
            raise ArtifactConflictError(f"{address} already holds different bytes")
        self._files[address] = data
        return hashlib.sha256(data).hexdigest()

    def get(self, run_id: str, name: str) -> bytes | None:
        return self._files.get(ArtifactAddress(run_id, name).relative_path())

    def names(self, run_id: str) -> list[str]:
        prefix = ArtifactAddress(run_id, "x").relative_path()[:-1]
        return sorted(path[len(prefix) :] for path in self._files if path.startswith(prefix))
