# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Transport-neutral read access to book runs."""

from engineering_influence.contracts.run.v1.run_summary_v1 import RunSummaryV1
from engineering_influence.controllers.interfaces.run_controller_interface import (
    RunControllerInterface,
)
from engineering_influence.services.interfaces.read_run_interface import ReadRunInterface


class RunController(RunControllerInterface):
    """Maps the read service's answers to the versioned contract every transport shares."""

    def __init__(self, reader: ReadRunInterface) -> None:
        """Remember the service that reads runs."""
        self._reader = reader

    def summary(self, run_id: str) -> RunSummaryV1:
        """Describe a run for an API or a command line."""
        run, artifacts = self._reader.summary(run_id)
        return RunSummaryV1.from_run(run, artifacts)

    def artifact(self, run_id: str, name: str) -> bytes:
        """The bytes of one stored artifact."""
        return self._reader.artifact(run_id, name)
