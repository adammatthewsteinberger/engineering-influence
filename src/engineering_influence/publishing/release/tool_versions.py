# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Versions of the external tools a build used, for the evidence report."""

import shutil
import subprocess  # nosec B404
import sys


class ToolVersions:
    """The first line of each tool's version banner, or None when it is not installed."""

    def of(self, command: str) -> str | None:
        """Ask one tool for its version."""
        executable = shutil.which(command)
        if not executable:
            return None
        # pdftoppm prints its banner for -v and does not accept --version.
        args = ["-v"] if command == "pdftoppm" else ["--version"]
        try:
            # Fixed argument list from a located executable; no shell.
            proc = subprocess.run(  # nosec B603
                [executable, *args], capture_output=True, text=True, timeout=15, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        lines = (proc.stdout or proc.stderr).strip().splitlines()
        return lines[0] if lines else None

    def environment(self) -> dict[str, str | None]:
        """Python and the toolchain the pipeline depends on."""
        return {
            "python": sys.version.split()[0],
            "latexmk": self.of("latexmk"),
            "tex4ebook": self.of("tex4ebook"),
            "pdftoppm": self.of("pdftoppm"),
            "epubcheck": self.of("epubcheck"),
        }
