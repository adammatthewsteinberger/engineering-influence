# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Keeps the computer awake with the platform's own tool: caffeinate on macOS, systemd-inhibit on Linux."""

import os
import platform
import shutil
import subprocess  # nosec B404
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import ClassVar

from engineering_influence.interfaces.keep_awake_interface import KeepAwakeInterface


class SystemKeepAwake(KeepAwakeInterface):
    """A sleep inhibitor that lasts as long as the block it wraps, and is stopped on every way out of it.

    On macOS it runs ``caffeinate -i -w <pid>``, which also ends with this process. On Linux it runs
    ``systemd-inhibit`` around a ``sleep``, which holds the lock until it is stopped. Where neither tool is
    found, the block runs anyway and a warning says the machine may sleep: a closed laptop lid on battery still
    sleeps on both platforms, whatever this does.

    The platform, the tool lookup, the process start and the warning are injected, so the choice is testable on
    any machine.
    """

    MAC: ClassVar[str] = "Darwin"
    LINUX: ClassVar[str] = "Linux"
    STOP_WAIT_SECONDS: ClassVar[float] = 5.0

    def __init__(
        self,
        system: str,
        find: Callable[[str], str | None],
        start: Callable[[list[str]], "subprocess.Popen[bytes]"],
        warn: Callable[[str], None],
    ) -> None:
        """Remember how to find and start the system's sleep inhibitor, and where to send warnings."""
        self._system = system
        self._find = find
        self._start = start
        self._warn = warn

    @classmethod
    def for_this_machine(cls) -> "SystemKeepAwake":
        """The inhibitor for the computer this runs on, with its warning on standard error."""
        return cls(platform.system(), shutil.which, cls._spawn, cls._warn_on_stderr)

    @staticmethod
    def _spawn(command: list[str]) -> "subprocess.Popen[bytes]":
        """Start the inhibitor with no shell and no input or output of its own."""
        return subprocess.Popen(  # nosec B603
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @staticmethod
    def _warn_on_stderr(line: str) -> None:
        print(line, file=sys.stderr)

    @contextmanager
    def hold(self) -> Iterator[None]:
        """Hold the lock for the block; if no tool exists, warn and run the block without one."""
        command = self._command()
        if command is None:
            self._warn(
                "warning: no sleep inhibitor is available on this machine, so the computer may sleep during the run; "
                "a run that is stopped by sleep can be continued with --resume"
            )
            yield
            return
        process = self._start(command)
        try:
            yield
        finally:
            self._stop(process)

    def _command(self) -> list[str] | None:
        if self._system == self.MAC and self._find("caffeinate"):
            return ["caffeinate", "-i", "-w", str(os.getpid())]
        if self._system == self.LINUX and self._find("systemd-inhibit"):
            return [
                "systemd-inhibit",
                "--what=sleep",
                "--who=engineering-influence",
                "--why=writing a book",
                "--mode=block",
                "sleep",
                "infinity",
            ]
        return None

    def _stop(self, process: "subprocess.Popen[bytes]") -> None:
        process.terminate()
        try:
            process.wait(timeout=self.STOP_WAIT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
