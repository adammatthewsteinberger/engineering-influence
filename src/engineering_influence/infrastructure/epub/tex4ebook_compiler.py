# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs tex4ebook (TeX4ht in LuaLaTeX mode) to turn the ebook LaTeX into EPUB 3."""

from pathlib import Path

from engineering_influence.infrastructure.process.interfaces.process_runner_interface import (
    ProcessRunnerInterface,
)
from engineering_influence.infrastructure.process.process_runner import ProcessRunner
from engineering_influence.infrastructure.typesetting.tool_environment import ToolEnvironment
from engineering_influence.interfaces.epub_compiler_interface import EpubCompilerInterface
from engineering_influence.models.tool_limits import ToolLimits


class Tex4ebookCompiler(EpubCompilerInterface):
    """Uses fine-ebook.cfg for the markup and fine-ebook.css for the styles.

    The conversion stops, with a BookBuildError, if it passes its time, memory or disk limit.
    """

    DEFAULT_LIMITS = ToolLimits(
        timeout_seconds=1800.0, max_memory_bytes=8 * 2**30, max_disk_bytes=4 * 2**30
    )

    def __init__(
        self, runner: ProcessRunnerInterface | None = None, limits: ToolLimits | None = None
    ) -> None:
        """Remember the process runner and limits the compiler runs under."""
        self._runner = runner or ProcessRunner()
        self._limits = limits or self.DEFAULT_LIMITS

    def compile(self, workdir: Path, tex_name: str) -> tuple[int, str]:
        """Run the conversion; return (exit status, stdout and stderr)."""
        command = ["tex4ebook", "-l", "-f", "epub3", "-c", "fine-ebook.cfg", tex_name]
        # Fixed argument list, no shell; tex_name is a validated slug plus '.tex'.
        status, stdout, stderr = self._runner.run(
            command, self._limits, cwd=workdir, env=ToolEnvironment().build(), watch=workdir
        )
        return status, stdout + stderr
