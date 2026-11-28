# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Lists the book runs the database holds, each as it was last saved."""

from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.services.interfaces.list_runs_interface import ListRunsInterface


class ListRuns(ListRunsInterface):
    """Reads every run id, then each run; a run deleted between the two reads is skipped."""

    def __init__(self, runs: RunRepositoryInterface) -> None:
        """Remember the run repository the runs are listed from."""
        self._runs = runs

    def runs(self) -> tuple[BookRun, ...]:
        """Every saved run, in the order the repository lists them."""
        found = (self._runs.get(run_id) for run_id in self._runs.run_ids())
        return tuple(run for run in found if run is not None)
