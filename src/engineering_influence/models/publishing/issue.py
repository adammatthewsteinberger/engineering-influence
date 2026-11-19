# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One manuscript audit issue."""

from dataclasses import dataclass


@dataclass
class Issue:
    """A severity-coded defect located in a source file."""

    severity: str
    code: str
    message: str
    path: str | None = None
    line: int | None = None
