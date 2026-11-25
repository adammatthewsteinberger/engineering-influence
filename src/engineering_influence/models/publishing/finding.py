# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One release-readiness finding."""

from dataclasses import dataclass

from engineering_influence.models.publishing.interfaces.finding_interface import FindingInterface


@dataclass
class Finding(FindingInterface):
    """A severity-coded observation about a release contract."""

    severity: str
    code: str
    message: str
    path: str | None = None
