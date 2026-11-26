# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""CommandCanonCheck: the configured command runs in the author's folder with no shell, and no command means no check."""

from pathlib import Path

import pytest

from engineering_influence.infrastructure.canon.command_canon_check import CommandCanonCheck
from engineering_influence.infrastructure.process.interfaces.process_runner_interface import (
    ProcessRunnerInterface,
)
from engineering_influence.models.tool_limits import ToolLimits


class RecordingRunner(ProcessRunnerInterface):
    def __init__(self, status: int = 0, stdout: str = "", stderr: str = "") -> None:
        self._result = (status, stdout, stderr)
        self.calls: list[tuple[list[str], Path | None]] = []

    def run(
        self,
        command: list[str],
        limits: ToolLimits,
        cwd: Path | None = None,
        env: object = None,
        watch: Path | None = None,
    ) -> tuple[int, str, str]:
        self.calls.append((command, cwd))
        return self._result


def test_no_command_means_no_check() -> None:
    assert CommandCanonCheck.from_environment({}) is None
    assert CommandCanonCheck.from_environment({"EI_SCREENPLAY_CANON_CHECK": "  "}) is None


def test_a_command_without_its_folder_is_refused() -> None:
    with pytest.raises(ValueError, match="EI_SCREENPLAY_CANON_FOLDER"):
        CommandCanonCheck.from_environment({"EI_SCREENPLAY_CANON_CHECK": "python3 check.py"})


def test_the_command_is_split_like_a_shell_and_runs_in_the_folder() -> None:
    runner = RecordingRunner()
    check = CommandCanonCheck.from_environment(
        {
            "EI_SCREENPLAY_CANON_CHECK": "python3 'scripts/canon check.py' --check",
            "EI_SCREENPLAY_CANON_FOLDER": "/author/folder",
        },
        runner,
    )
    assert check is not None
    check.run()
    assert runner.calls == [
        (["python3", "scripts/canon check.py", "--check"], Path("/author/folder")),
    ]


def test_the_output_is_stdout_and_stderr_together() -> None:
    runner = RecordingRunner(status=1, stdout="ERROR a: [r] one\n", stderr="WARN b: [r] two\n")
    assert CommandCanonCheck(["check"], Path("/f"), runner).run() == (
        1,
        "ERROR a: [r] one\nWARN b: [r] two\n",
    )
