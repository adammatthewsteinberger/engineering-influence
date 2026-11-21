# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs tex4ebook (TeX4ht in LuaLaTeX mode) to turn the ebook LaTeX into EPUB 3."""

from pathlib import Path

from engineering_influence.infrastructure.process.interfaces.process_runner_interface import (
    ProcessRunnerInterface,
)
from engineering_influence.infrastructure.process.process_runner import ProcessRunner
from engineering_influence.infrastructure.typesetting.tool_environment import ToolEnvironment
from engineering_influence.interfaces.epub_compiler_interface import EpubCompilerInterface


class Tex4ebookCompiler(EpubCompilerInterface):
    """Uses fine-ebook.cfg for the markup and fine-ebook.css for the styles.

    The conversion stops, with a BookBuildError, if it runs past ``timeout_seconds``.
    """

    def __init__(
        self, runner: ProcessRunnerInterface | None = None, timeout_seconds: float = 1800.0
    ) -> None:
        self._runner = runner or ProcessRunner()
        self._timeout = timeout_seconds

    def compile(self, workdir: Path, tex_name: str) -> tuple[int, str]:
        """Run the conversion; return (exit status, stdout and stderr)."""
        command = ["tex4ebook", "-l", "-f", "epub3", "-c", "fine-ebook.cfg", tex_name]
        # Fixed argument list, no shell; tex_name is a validated slug plus '.tex'.
        status, stdout, stderr = self._runner.run(
            command, self._timeout, cwd=workdir, env=ToolEnvironment().build()
        )
        return status, stdout + stderr
