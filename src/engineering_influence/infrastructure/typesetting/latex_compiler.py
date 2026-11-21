# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs latexmk with LuaLaTeX."""

from pathlib import Path

from engineering_influence.infrastructure.process.interfaces.process_runner_interface import (
    ProcessRunnerInterface,
)
from engineering_influence.infrastructure.process.process_runner import ProcessRunner
from engineering_influence.infrastructure.typesetting.tool_environment import ToolEnvironment
from engineering_influence.interfaces.latex_compiler_interface import LatexCompilerInterface


class LatexCompiler(LatexCompilerInterface):
    """Iterates until cross-references, and so the contents page numbers, are stable.

    The build stops, with a BookBuildError, if it runs past ``timeout_seconds``.
    """

    def __init__(
        self, runner: ProcessRunnerInterface | None = None, timeout_seconds: float = 1800.0
    ) -> None:
        self._runner = runner or ProcessRunner()
        self._timeout = timeout_seconds

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
        status, stdout, _ = self._runner.run(command, self._timeout, cwd=workdir, env=env)
        return status, stdout
