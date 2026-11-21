# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs an external tool under limits, and stops the whole process tree when it passes one."""

import os
import signal
import subprocess  # nosec B404
import time
from collections.abc import Mapping
from pathlib import Path
from typing import NoReturn

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.process.interfaces.process_meter_interface import (
    ProcessMeterInterface,
)
from engineering_influence.infrastructure.process.interfaces.process_runner_interface import (
    ProcessRunnerInterface,
)
from engineering_influence.infrastructure.process.process_meter import ProcessMeter
from engineering_influence.models.tool_limits import ToolLimits


class ProcessRunner(ProcessRunnerInterface):
    """A build that never finishes, or eats the machine, must fail the run, not hang it.

    ``subprocess.run(timeout=...)`` stops only the direct child, and then waits for the output
    pipes to close. ``latexmk`` starts ``lualatex`` and ``tex4ebook`` starts a chain of tools, so
    a grandchild keeps the pipe open and the call still hangs. Here the tool gets its own
    session, so the tool and everything it started share one process group, and the group is
    killed. Output is then read for a short time only, in case something outside the group still
    holds the pipes.

    Memory and disk are sampled every ``sample_seconds`` while the tool runs, so a limit is
    enforced to within what the tool can allocate or write in one interval.

    This needs process groups, so it works on Linux and macOS.
    """

    TAIL_CHARACTERS = 2000

    def __init__(
        self,
        drain_seconds: float = 5.0,
        meter: ProcessMeterInterface | None = None,
        sample_seconds: float = 0.5,
    ) -> None:
        self._drain_seconds = drain_seconds
        self._meter = meter or ProcessMeter()
        self._sample_seconds = sample_seconds

    def run(
        self,
        command: list[str],
        limits: ToolLimits,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        watch: Path | None = None,
    ) -> tuple[int, str, str]:
        """Run the command; return (exit status, stdout, stderr).

        Raises BookBuildError when the tool passes its time, memory or disk limit, once the
        tool and everything it started have been stopped. The disk limit applies to the
        directory named by ``watch``; with none given, disk is not measured.
        """
        # Argument list from the caller's fixed commands, no shell; the Popen block closes the
        # pipes and reaps the child however it is left.
        with subprocess.Popen(  # nosec B603
            command,
            cwd=cwd,
            env=None if env is None else dict(env),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        ) as process:
            try:
                stdout, stderr = self._wait(process, command, limits, watch)
            except BookBuildError:
                raise  # the tool was already stopped
            except BaseException:
                # An interrupt must not leave a build running behind the parent.
                self._kill(process)
                raise
        return process.returncode, stdout, stderr

    def _wait(
        self,
        process: "subprocess.Popen[str]",
        command: list[str],
        limits: ToolLimits,
        watch: Path | None,
    ) -> tuple[str, str]:
        """Wait for the tool in short slices, stopping it at the first limit it passes."""
        deadline = time.monotonic() + limits.timeout_seconds
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                self._stop(
                    process, command, f"did not finish within {limits.timeout_seconds:g} seconds"
                )
            try:
                return process.communicate(timeout=min(self._sample_seconds, left))
            except subprocess.TimeoutExpired:
                problem = self._over_limit(process, limits, watch)
                if problem:
                    self._stop(process, command, problem)

    def _over_limit(
        self, process: "subprocess.Popen[str]", limits: ToolLimits, watch: Path | None
    ) -> str | None:
        """What the tool has passed, or None while it is inside its memory and disk limits."""
        memory = self._meter.memory_bytes(process.pid)
        if memory > limits.max_memory_bytes:
            return (
                f"used {self._mib(memory)} of memory, over its limit of "
                f"{self._mib(limits.max_memory_bytes)}"
            )
        if watch is not None:
            disk = self._meter.disk_bytes(watch)
            if disk > limits.max_disk_bytes:
                return (
                    f"wrote {self._mib(disk)} to disk, over its limit of "
                    f"{self._mib(limits.max_disk_bytes)}"
                )
        return None

    def _mib(self, size: int) -> str:
        return f"{size / 2**20:.0f} MiB"

    def _stop(self, process: "subprocess.Popen[str]", command: list[str], problem: str) -> NoReturn:
        """Kill the tool's tree and fail the build, saying what the tool had written."""
        self._kill(process)
        tail = "".join(self._drain(process))[-self.TAIL_CHARACTERS :]
        raise BookBuildError(f"{command[0]} {problem} and was stopped. The last output:\n{tail}")

    def _kill(self, process: "subprocess.Popen[str]") -> None:
        """Kill the tool's process group, then reap the leader.

        The leader is not reaped until the end, so its id is still ours when the group is
        killed. It is reaped here because ``Popen`` skips that wait after a KeyboardInterrupt
        and would leave the dead leader behind.
        """
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # everything in the group has already exited
        process.wait()

    def _drain(self, process: "subprocess.Popen[str]") -> tuple[str, str]:
        """What the killed tool wrote, waiting only briefly for the pipes to close."""
        try:
            return process.communicate(timeout=self._drain_seconds)
        except subprocess.TimeoutExpired:
            return "", ""  # a process outside the group holds the pipes; leaving closes ours
