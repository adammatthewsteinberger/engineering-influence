# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs epubcheck, the reference validator, when it is installed."""

import shutil
from pathlib import Path

from engineering_influence.infrastructure.process.interfaces.process_runner_interface import (
    ProcessRunnerInterface,
)
from engineering_influence.infrastructure.process.process_runner import ProcessRunner
from engineering_influence.interfaces.epubcheck_interface import EpubcheckInterface
from engineering_influence.models.tool_limits import ToolLimits


class EpubcheckRunner(EpubcheckInterface):
    """Finds epubcheck on PATH (Debian installs it as a bare .jar) and reports its findings.

    It writes nothing, so only its time and memory are limited; a JVM may hold a good deal.
    """

    DEFAULT_LIMITS = ToolLimits(
        timeout_seconds=600.0, max_memory_bytes=4 * 2**30, max_disk_bytes=2**30
    )

    def __init__(
        self,
        required: bool = False,
        runner: ProcessRunnerInterface | None = None,
        limits: ToolLimits | None = None,
    ) -> None:
        """Remember whether epubcheck is required, and the process runner and limits it uses."""
        self._required = required
        self._runner = runner or ProcessRunner()
        self._limits = limits or self.DEFAULT_LIMITS

    def command(self) -> list[str] | None:
        """epubcheck as a command, or None when it is not installed."""
        found = shutil.which("epubcheck")
        if not found:
            return None
        real = Path(found).resolve()
        if real.suffix == ".jar":
            return ["java", "-jar", str(real)] if shutil.which("java") else None
        return [found]

    def run(self, path: Path) -> list[str]:
        """Return up to 20 epubcheck findings.

        Empty when it passes. When epubcheck is not installed that is also empty, unless it
        is required (a strict release): a validator that did not run must not read as a pass.
        """
        command = self.command()
        if not command:
            if self._required:
                return ["epubcheck: not installed, but a strict release requires it"]
            return []
        # Argument list built from a located executable and a file path; no shell.
        status, stdout, stderr = self._runner.run([*command, "--quiet", str(path)], self._limits)
        if status == 0:
            return []
        lines = (stdout + stderr).strip().splitlines()
        report = [
            line
            for line in lines
            if line.strip() and not line.startswith("Picked up JAVA_TOOL_OPTIONS")
        ]
        return [f"epubcheck: {line}" for line in report[:20]]
