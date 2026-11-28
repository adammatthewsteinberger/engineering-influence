# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Artifact store on a local directory."""

import hashlib
from pathlib import Path

from engineering_influence.errors.artifact_conflict_error import ArtifactConflictError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.path_guard_interface import PathGuardInterface
from engineering_influence.models.artifact_address import RESERVED_SUFFIX, ArtifactAddress


class FileArtifactStore(ArtifactStoreInterface):
    """One file per artifact under ``root/<run_id>/<name>``, written to a temporary name first.

    A crash mid-write leaves only a ``.part`` file, which is never listed or read, so a file
    under its real name is always complete. The path guard resolves symlinks, so a link
    planted inside a run directory cannot lead a write outside ``root``.
    """

    def __init__(self, root: Path, guard: PathGuardInterface) -> None:
        """Remember the folder that holds the artifacts and the path guard that keeps names inside it."""
        self._root = root
        self._guard = guard

    def put(self, run_id: str, name: str, data: bytes) -> str:
        """Store the bytes under the run's name, refusing to replace different bytes already there, and return their SHA-256 digest."""
        path = self._path(run_id, name)
        if path.exists():
            if path.read_bytes() != data:
                raise ArtifactConflictError(f"{run_id}/{name} already holds different bytes")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            partial = path.with_name(path.name + RESERVED_SUFFIX)
            partial.write_bytes(data)
            partial.replace(path)
        return hashlib.sha256(data).hexdigest()

    def get(self, run_id: str, name: str) -> bytes | None:
        """The bytes stored under the run's name, or None when there are none."""
        path = self._path(run_id, name)
        return path.read_bytes() if path.is_file() else None

    def names(self, run_id: str) -> list[str]:
        """The names of every artifact stored for the run, relative to the run's folder, sorted."""
        base = self._path(run_id, "x").parent
        if not base.is_dir():
            return []
        return sorted(
            found.relative_to(base).as_posix()
            for found in base.rglob("*")
            if found.is_file() and not found.name.endswith(RESERVED_SUFFIX)
        )

    def _path(self, run_id: str, name: str) -> Path:
        return self._guard.confine(ArtifactAddress(run_id, name).relative_path(), self._root)
