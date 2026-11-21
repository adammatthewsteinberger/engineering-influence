# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a book run and its artifacts."""

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.services.interfaces.read_run_interface import ReadRunInterface


class ReadRun(ReadRunInterface):
    """Read-only: it never saves a run or stores an artifact.

    A name that could never be stored (absolute, climbing, with a backslash) is reported as a
    missing artifact, the same as a name that was simply never written, so a caller cannot tell the
    two apart and nothing about the store's layout leaks.
    """

    def __init__(self, runs: RunRepositoryInterface, artifacts: ArtifactStoreInterface) -> None:
        self._runs = runs
        self._artifacts = artifacts

    def summary(self, run_id: str) -> tuple[BookRun, list[str]]:
        """The run and the names of its stored artifacts; ``RUN_NOT_FOUND`` if there is no run."""
        run = self._runs.get(run_id)
        if run is None:
            raise ApplicationError(
                code="RUN_NOT_FOUND", message=f"no run {run_id!r}", http_status=404
            )
        return run, self._artifacts.names(run_id)

    def artifact(self, run_id: str, name: str) -> bytes:
        """One stored artifact; ``ARTIFACT_NOT_FOUND`` if there is none, or the name is invalid."""
        try:
            data = self._artifacts.get(run_id, name)
        except ValueError:
            data = None
        if data is None:
            raise ApplicationError(
                code="ARTIFACT_NOT_FOUND",
                message=f"run {run_id!r} has no artifact {name!r}",
                http_status=404,
            )
        return data
