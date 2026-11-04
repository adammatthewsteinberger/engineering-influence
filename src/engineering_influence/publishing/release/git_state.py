# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where the repository stood when a release was built."""

import subprocess  # nosec B404
from pathlib import Path
from typing import Any


class GitState:
    """Commit, branch, and dirty status; None for each when git is unavailable."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def read(self) -> dict[str, Any]:
        """The state of the repository at the project root."""
        return {
            "commit": self._run("rev-parse", "HEAD"),
            "branch": self._run("branch", "--show-current"),
            "status": self._run("status", "--short"),
        }

    def _run(self, *args: str) -> str | None:
        try:
            # Fixed git subcommands; no shell.
            proc = subprocess.run(  # nosec B603 B607
                ["git", *args],
                cwd=self._root,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return proc.stdout.strip() if proc.returncode == 0 else None
