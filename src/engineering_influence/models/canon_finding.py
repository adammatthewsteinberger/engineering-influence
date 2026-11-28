# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One finding of the author's canon check: a severity, where it is, the rule it breaks, and the message."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.canon_finding_interface import CanonFindingInterface


@dataclass(frozen=True, slots=True)
class CanonFinding(CanonFindingInterface):
    """`severity` is `ERROR` or `WARN`. The check's own words are kept as written."""

    SEVERITIES = ("ERROR", "WARN")

    severity: str
    where: str
    rule: str
    message: str

    def __post_init__(self) -> None:
        if self.severity not in self.SEVERITIES:
            raise ValueError(f"a canon finding is ERROR or WARN, not {self.severity!r}")
        for name, value in (("where", self.where), ("rule", self.rule), ("message", self.message)):
            if not value.strip():
                raise ValueError(f"a canon finding has a {name}")

    def is_error(self) -> bool:
        """True for an ERROR finding."""
        return self.severity == "ERROR"
