# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs latexmk with LuaLaTeX."""

import subprocess  # nosec B404
from pathlib import Path

from engineering_influence.infrastructure.typesetting.tool_environment import ToolEnvironment
from engineering_influence.interfaces.latex_compiler_interface import LatexCompilerInterface


class LatexCompiler(LatexCompilerInterface):
    """Iterates until cross-references, and so the contents page numbers, are stable."""

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
        result = subprocess.run(  # nosec B603
            command, cwd=workdir, capture_output=True, text=True, env=env, check=False
        )
        return result.returncode, result.stdout
