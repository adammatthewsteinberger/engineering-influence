# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs one pipeline step and records the evidence for it."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from engineering_influence.interfaces.clock_interface import ClockInterface
from engineering_influence.interfaces.step_recorder_interface import StepRecorderInterface
from engineering_influence.models.publishing.path_relativizer import PathRelativizer


class StepRecorder(StepRecorderInterface):
    """A step passes when it returns and fails when it raises; either way it is logged."""

    def __init__(self, relativizer: PathRelativizer, clock: ClockInterface) -> None:
        self._relativizer = relativizer
        self._clock = clock

    def run(
        self, name: str, command: list[str], action: Callable[[], str], log_path: Path
    ) -> dict[str, Any]:
        """Run the action, write its output (or error) to log_path, and return the record."""
        started = self._clock.now()
        failed = False
        try:
            output = action()
        except (OSError, ValueError, RuntimeError) as error:
            output, failed = str(error), True
        log_path.write_text(output, encoding="utf-8")
        return {
            "name": name,
            "command": command,
            "status": "fail" if failed else "pass",
            "returncode": 1 if failed else 0,
            "started_at": started.isoformat(),
            "finished_at": self._clock.now().isoformat(),
            "log": self._relativizer.relative(log_path),
            "stdout_tail": output[-4000:],
        }
