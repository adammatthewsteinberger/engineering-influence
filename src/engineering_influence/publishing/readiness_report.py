# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The release-readiness report."""

from dataclasses import asdict, dataclass, field

from engineering_influence.publishing.finding import Finding


@dataclass
class ReadinessReport:
    """Metadata, pricing, and format decisions plus every finding about them."""

    schema_version: int
    slug: str
    status: str
    config: str
    page_count: int | None
    counts: dict[str, int | float] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)
    pricing: dict[str, object] = field(default_factory=dict)
    formats: dict[str, object] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def add(self, severity: str, code: str, message: str, path: str | None = None) -> None:
        """Record a finding."""
        self.findings.append(Finding(severity, code, message, path))

    @property
    def errors(self) -> list[Finding]:
        """Findings that block a release."""
        return [finding for finding in self.findings if finding.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        """Findings that do not block a release."""
        return [finding for finding in self.findings if finding.severity == "warning"]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-ready dictionary."""
        return asdict(self)
