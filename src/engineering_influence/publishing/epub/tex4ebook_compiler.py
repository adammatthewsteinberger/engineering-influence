# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs tex4ebook (TeX4ht in LuaLaTeX mode) to turn the ebook LaTeX into EPUB 3."""

import subprocess  # nosec B404
from pathlib import Path


class Tex4ebookCompiler:
    """Uses fine-ebook.cfg for the markup and fine-ebook.css for the styles."""

    def compile(self, workdir: Path, tex_name: str) -> tuple[int, str]:
        """Run the conversion; return (exit status, stdout and stderr)."""
        command = ["tex4ebook", "-l", "-f", "epub3", "-c", "fine-ebook.cfg", tex_name]
        # Fixed argument list, no shell; tex_name is a validated slug plus '.tex'.
        result = subprocess.run(  # nosec B603
            command, cwd=workdir, capture_output=True, text=True, check=False
        )
        return result.returncode, result.stdout + result.stderr
