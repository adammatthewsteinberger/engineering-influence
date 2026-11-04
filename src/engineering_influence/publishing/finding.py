# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One release-readiness finding."""

from dataclasses import dataclass


@dataclass
class Finding:
    """A severity-coded observation about a release contract."""

    severity: str
    code: str
    message: str
    path: str | None = None
