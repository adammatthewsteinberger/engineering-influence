# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs latexmk with LuaLaTeX."""

from pathlib import Path

from engineering_influence.infrastructure.process.interfaces.process_runner_interface import (
    ProcessRunnerInterface,
)
from engineering_influence.infrastructure.process.process_runner import ProcessRunner
from engineering_influence.infrastructure.typesetting.tool_environment import ToolEnvironment
from engineering_influence.interfaces.latex_compiler_interface import LatexCompilerInterface
from engineering_influence.models.tool_limits import ToolLimits


class LatexCompiler(LatexCompilerInterface):
    """Iterates until cross-references, and so the contents page numbers, are stable.

    The build stops, with a BookBuildError, if it passes its time, memory or disk limit.
    """

    DEFAULT_LIMITS = ToolLimits(
        timeout_seconds=1800.0, max_memory_bytes=8 * 2**30, max_disk_bytes=4 * 2**30
    )

    def __init__(
        self, runner: ProcessRunnerInterface | None = None, limits: ToolLimits | None = None
    ) -> None:
        self._runner = runner or ProcessRunner()
        self._limits = limits or self.DEFAULT_LIMITS

    def compile(self, workdir: Path, tex_name: str, source_date_epoch: int) -> tuple[int, str]:
        """Run the build; return (exit status, captured stdout).

        SOURCE_DATE_EPOCH pins the PDF creation date so rebuilding unchanged sources does not
        create a meaningless binary diff.
        """
        command = [
            "latexmk",
            "-lualatex",
            "-no-shell-escape",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            tex_name,
        ]
        env = ToolEnvironment().build(source_date_epoch)
        # Fixed argument list, no shell; tex_name is a validated slug plus '.tex'.
        status, stdout, _ = self._runner.run(
            command, self._limits, cwd=workdir, env=env, watch=workdir
        )
        return status, stdout
