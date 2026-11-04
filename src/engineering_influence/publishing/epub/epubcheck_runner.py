# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs epubcheck, the reference validator, when it is installed."""

import shutil
import subprocess  # nosec B404
from pathlib import Path


class EpubcheckRunner:
    """Finds epubcheck on PATH (Debian installs it as a bare .jar) and reports its findings."""

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
        """Return up to 20 epubcheck findings; empty when it passes or is not installed."""
        command = self.command()
        if not command:
            return []
        # Argument list built from a located executable and a file path; no shell.
        proc = subprocess.run(  # nosec B603
            [*command, "--quiet", str(path)], capture_output=True, text=True, check=False
        )
        if proc.returncode == 0:
            return []
        lines = (proc.stdout + proc.stderr).strip().splitlines()
        report = [
            line
            for line in lines
            if line.strip() and not line.startswith("Picked up JAVA_TOOL_OPTIONS")
        ]
        return [f"epubcheck: {line}" for line in report[:20]]
