# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Output checks for a run that has nothing to check."""

from engineering_influence.interfaces.stage_output_check_interface import (
    StageOutputCheckInterface,
)


class NoOutputChecks(StageOutputCheckInterface):
    """Accepts every answer, for stages whose output nothing parses."""

    def check(self, stage: str, text: str) -> None:
        """Accept the answer."""
