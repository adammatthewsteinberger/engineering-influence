# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A defect a run found and either fixed, tolerated or could not fix."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.quality_issue_interface import QualityIssueInterface


@dataclass(frozen=True, slots=True)
class QualityIssue(QualityIssueInterface):
    """What went wrong, where, and whether it stops a release."""

    stage: str
    code: str
    detail: str
    blocking: bool = False

    def __post_init__(self) -> None:
        """Validate the issue's fields when it is built."""
        if not self.stage.strip() or not self.code.strip():
            raise ValueError("quality issue stage and code are required")
