# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An artifact store whose files are objects in a bucket, so the run's files outlive the worker that wrote them."""

import hashlib

from engineering_influence.errors.artifact_conflict_error import ArtifactConflictError
from engineering_influence.infrastructure.object_storage.interfaces.s3_object_store_interface import (
    S3ObjectStoreInterface,
)
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.models.artifact_address import ArtifactAddress


class S3ArtifactStore(ArtifactStoreInterface):
    """Each artifact is the object `prefix/run_id/name` in `bucket`. Write-once, as the file store is: the same bytes
    are accepted again and different bytes are refused. The check reads before it writes, so two writers racing on one
    name are not serialised by this class; a run's artifacts are written by one worker at a time."""

    def __init__(self, objects: S3ObjectStoreInterface, bucket: str, prefix: str = "runs") -> None:
        """Remember the object store, the bucket, and the key prefix for artifacts."""
        if not bucket.strip() or not prefix.strip():
            raise ValueError("an object store needs a bucket and a prefix")
        self._objects = objects
        self._bucket = bucket
        self._prefix = prefix.strip("/")

    def put(self, run_id: str, name: str, data: bytes) -> str:
        """Store the bytes under the run's key, refusing to replace different bytes already there, and return their SHA-256 digest."""
        key = self._key(run_id, name)
        existing = self._objects.get(self._bucket, key)
        if existing is None:
            self._objects.put(self._bucket, key, data)
        elif existing != data:
            raise ArtifactConflictError(f"{run_id}/{name} already holds different bytes")
        return hashlib.sha256(data).hexdigest()

    def get(self, run_id: str, name: str) -> bytes | None:
        """The bytes stored under the run's key, or None when there are none."""
        return self._objects.get(self._bucket, self._key(run_id, name))

    def names(self, run_id: str) -> list[str]:
        """The names of every artifact stored for the run, relative to the run's prefix."""
        base = self._run_prefix(run_id)
        return [key[len(base) :] for key in self._objects.keys(self._bucket, base)]

    def close(self) -> None:
        """Nothing to release: the store holds no connection of its own; the S3 client is the runtime's to close."""

    def _key(self, run_id: str, name: str) -> str:
        return f"{self._prefix}/{ArtifactAddress(run_id, name).relative_path()}"

    def _run_prefix(self, run_id: str) -> str:
        return f"{self._prefix}/{ArtifactAddress(run_id, 'x').run_id}/"
