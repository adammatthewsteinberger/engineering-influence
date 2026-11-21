# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Measures a process group's resident memory and a directory's size."""

import os
import subprocess  # nosec B404
from pathlib import Path

from engineering_influence.infrastructure.process.interfaces.process_meter_interface import (
    ProcessMeterInterface,
)


class ProcessMeter(ProcessMeterInterface):
    """Memory comes from ``ps``, which reports it the same way on Linux and macOS.

    Resident memory is sampled, so a tool that allocates faster than the sampling interval
    can pass its limit before it is seen; the overshoot is bounded by how much it can touch
    in one interval. A process that has left the group is not counted.
    """

    def memory_bytes(self, group: int) -> int:
        """Resident memory of every process in the group, in bytes; 0 when none is left."""
        # Fixed arguments, no shell.
        listing = subprocess.run(  # nosec B603 B607
            ["ps", "-axo", "pgid=,rss="],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
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
