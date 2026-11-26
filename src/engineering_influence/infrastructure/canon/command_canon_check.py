# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs the author's canon check command in the author's folder. The command is configured, never shipped here."""

from __future__ import annotations

import shlex
from collections.abc import Mapping
from pathlib import Path

from engineering_influence.infrastructure.process.interfaces.process_runner_interface import (
    ProcessRunnerInterface,
)
from engineering_influence.infrastructure.process.process_runner import ProcessRunner
from engineering_influence.interfaces.canon_check_interface import CanonCheckInterface
from engineering_influence.models.tool_limits import ToolLimits


class CommandCanonCheck(CanonCheckInterface):
    """The command is split into words the way a shell would split it, and run with no shell, in the author's folder.
    This repository never holds the author's canon; the command reads the author's own files there.

    The check only reads, so only its time and memory are limited.
    """

    LIMITS = ToolLimits(timeout_seconds=600.0, max_memory_bytes=2 * 2**30, max_disk_bytes=2**30)

    def __init__(
        self,
        command: list[str],
        folder: Path,
        runner: ProcessRunnerInterface | None = None,
    ) -> None:
        self._command = command
        self._folder = folder
        self._runner = runner or ProcessRunner()

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str],
        runner: ProcessRunnerInterface | None = None,
    ) -> CommandCanonCheck | None:
        """The check the environment names, or None when none is named. Naming a command without its folder is refused:
        the check reads the author's files, and it must not run somewhere else."""
        command = environment.get("EI_SCREENPLAY_CANON_CHECK", "").strip()
        if not command:
            return None
        folder = environment.get("EI_SCREENPLAY_CANON_FOLDER", "").strip()
        if not folder:
            raise ValueError(
                "EI_SCREENPLAY_CANON_CHECK needs EI_SCREENPLAY_CANON_FOLDER, the folder it runs in"
            )
        return cls(shlex.split(command), Path(folder), runner)

    def run(self) -> tuple[int, str]:
        status, stdout, stderr = self._runner.run(self._command, self.LIMITS, cwd=self._folder)
        return status, stdout + stderr
