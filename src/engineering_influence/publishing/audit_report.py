"""The manuscript audit report."""

from dataclasses import asdict, dataclass, field
from typing import Any

from engineering_influence.publishing.entry import Entry
from engineering_influence.publishing.issue import Issue


@dataclass
class AuditReport:
    """Inventory, thresholds, and issues for one configured manuscript."""

    schema_version: int
    slug: str
    config: str
    source: str
    status: str = "pass"
    counts: dict[str, int | float] = field(default_factory=dict)
    thresholds: dict[str, int | float | bool] = field(default_factory=dict)
    entries: list[Entry] = field(default_factory=list)
    style_formula_counts: dict[str, int] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        """Blocking issues."""
        return self.issues

    def add(self, issue: Issue) -> None:
        """File an issue under warnings or blocking issues."""
        if issue.severity == "warning":
            self.warnings.append(issue)
        else:
            self.issues.append(issue)

    def finish(self) -> None:
        """Set the overall status."""
        self.status = "fail" if self.issues else "pass"

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-ready dictionary."""
        return asdict(self)
