# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Lists, resumes and cancels book runs by composing the three services that do each."""

from engineering_influence.models.book_run import BookRun
from engineering_influence.services.interfaces.cancel_run_interface import CancelRunInterface
from engineering_influence.services.interfaces.list_runs_interface import ListRunsInterface
from engineering_influence.services.interfaces.resume_run_interface import ResumeRunInterface
from engineering_influence.services.interfaces.run_management_interface import (
    RunManagementInterface,
)


class RunManagement(RunManagementInterface):
    """One place for the transports to reach run control; each operation is the service that owns it.

    The rules live in those services (a missing run is refused, a finished run cannot be resumed, and so on), so
    the API, MCP and SDK refuse exactly what the command line refuses.
    """

    def __init__(
        self,
        lister: ListRunsInterface,
        resumer: ResumeRunInterface,
        canceller: CancelRunInterface,
    ) -> None:
        self._lister = lister
        self._resumer = resumer
        self._canceller = canceller

    def runs(self) -> tuple[BookRun, ...]:
        """Every saved run."""
        return self._lister.runs()

    def resume(self, run_id: str) -> BookRun:
        """Un-park a parked run and queue its current stage."""
        return self._resumer.resume(run_id)

    def cancel(self, run_id: str) -> BookRun:
        """Stop a run for good."""
        return self._canceller.cancel(run_id)
