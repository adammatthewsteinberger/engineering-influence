# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ProcessRunner."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from engineering_influence.models.tool_limits import ToolLimits


class ProcessRunnerInterface(ABC):
    """Runs an external tool and never lets it pass its limits."""

    __slots__ = ()

    @abstractmethod
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
