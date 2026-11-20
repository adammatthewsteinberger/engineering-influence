# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The outcome of evaluating one gate."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.gate_verdict_interface import GateVerdictInterface
from engineering_influence.models.quality_issue import QualityIssue


@dataclass(frozen=True, slots=True)
class GateVerdict(GateVerdictInterface):
    """Pass or fail for a named gate, with the issues behind the answer."""

    gate: str
    passed: bool
    issues: tuple[QualityIssue, ...] = ()

    def __post_init__(self) -> None:
        if not self.gate.strip():
            raise ValueError("gate verdict needs the gate's name")
        if not self.passed and not self.issues:
            raise ValueError("a failed verdict must say why")
        if self.passed and any(issue.blocking for issue in self.issues):
            raise ValueError("a passing verdict cannot carry a blocking issue")
