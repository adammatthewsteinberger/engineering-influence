# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Measures a process group's resident memory and a directory's size."""

import os
import subprocess  # nosec B404
from collections.abc import Callable
from pathlib import Path

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.process.interfaces.process_meter_interface import (
    ProcessMeterInterface,
)


class ProcessMeter(ProcessMeterInterface):
    """Memory comes from ``ps``, which reports it the same way on Linux and macOS.

    Resident memory is sampled, so a tool that allocates faster than the sampling interval
    can pass its limit before it is seen; the overshoot is bounded by how much it can touch
    in one interval. A process that has left the group is not counted.

    ``ps`` is run from where the system keeps it, not looked up on ``PATH``: a tool is often run with a
    ``PATH`` of its own, and a measuring command that is found only through it would fail the first time a
    tool lasted past one sampling interval (and could be replaced by whatever a ``PATH`` entry holds).
    ``PATH`` is the fallback only when neither place has it.
    """

    LOCATIONS = ("/bin/ps", "/usr/bin/ps")

    def __init__(
        self,
        exists: Callable[[str], bool] = os.path.exists,
        fallback: str = "ps",
    ) -> None:
        self._exists = exists
        self._fallback = fallback

    def _ps(self) -> str:
        return next((place for place in self.LOCATIONS if self._exists(place)), self._fallback)

    def memory_bytes(self, group: int) -> int:
        """Resident memory of every process in the group, in bytes; 0 when none is left.

        Raises BookBuildError when there is no ``ps`` to ask, rather than an error that stops the run without
        saying why: the fix is to install ``procps``, and the message says so.
        """
        # Fixed arguments, no shell.
        try:
            listing = subprocess.run(  # nosec B603
                [self._ps(), "-axo", "pgid=,rss="],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            ).stdout
        except FileNotFoundError as error:
            raise BookBuildError(
                "this machine has no ps, which the build uses to measure a tool's memory; "
                "install the procps package (the worker image includes it)"
            ) from error
        kib = 0
        for line in listing.splitlines():
            pgid, rss = line.split()
            if int(pgid) == group:
                kib += int(rss)
        return kib * 1024

    def disk_bytes(self, directory: Path) -> int:
        """Total size of the files under the directory, in bytes; 0 when it does not exist.

        Symbolic links are not followed, and an entry that cannot be read counts as nothing.
        """
        total = 0
        for folder, _, names in os.walk(directory):
            for name in names:
                try:
                    total += os.lstat(Path(folder, name)).st_size
                except OSError:
                    continue
        return total
