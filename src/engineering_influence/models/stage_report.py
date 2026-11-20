# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a stage reports when it finishes."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.stage_report_interface import StageReportInterface
from engineering_influence.models.quality_issue import QualityIssue


@dataclass(frozen=True, slots=True)
class StageReport(StageReportInterface):
    """The issues a stage found and tolerated; a stage that cannot continue raises instead."""

    issues: tuple[QualityIssue, ...] = ()
