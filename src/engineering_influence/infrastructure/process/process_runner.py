# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs an external tool under a deadline, and stops the whole process tree when it passes."""

import os
import signal
import subprocess  # nosec B404
from collections.abc import Mapping
from pathlib import Path

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.process.interfaces.process_runner_interface import (
    ProcessRunnerInterface,
)


class ProcessRunner(ProcessRunnerInterface):
    """A build that never finishes must fail the run, not hang it.

    ``subprocess.run(timeout=...)`` stops only the direct child, and then waits for the output
    pipes to close. ``latexmk`` starts ``lualatex`` and ``tex4ebook`` starts a chain of tools, so
    a grandchild keeps the pipe open and the call still hangs. Here the tool gets its own
    session, so the tool and everything it started share one process group, and the group is
    killed. Output is then read for a short time only, in case something outside the group still
    holds the pipes.

    This needs process groups, so it works on Linux and macOS. On Windows a timeout would find
    no ``killpg`` and the build would stay hung, as every build did before there was a deadline.
    """

    TAIL_CHARACTERS = 2000

    def __init__(self, drain_seconds: float = 5.0) -> None:
        self._drain_seconds = drain_seconds

    def run(
        self,
        command: list[str],
        timeout_seconds: float,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> tuple[int, str, str]:
        """Run the command; return (exit status, stdout, stderr).

        Raises BookBuildError when the tool is still running after timeout_seconds, once the
        tool and everything it started have been stopped.
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
                stdout, stderr = process.communicate(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                self._kill(process)
                tail = "".join(self._drain(process))[-self.TAIL_CHARACTERS :]
                raise BookBuildError(
                    f"{command[0]} did not finish within {timeout_seconds:g} seconds and was "
                    f"stopped. The last output:\n{tail}"
                ) from None
            except BaseException:
                # An interrupt must not leave a build running behind the parent.
                self._kill(process)
                raise
        return process.returncode, stdout, stderr

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
