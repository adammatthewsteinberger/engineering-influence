# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ProcessRunner."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


class ProcessRunnerInterface(ABC):
    """Runs an external tool and never lets it run past a deadline."""

    __slots__ = ()

    @abstractmethod
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
