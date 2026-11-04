"""One release-readiness finding."""

from dataclasses import dataclass


@dataclass
class Finding:
    """A severity-coded observation about a release contract."""

    severity: str
    code: str
    message: str
    path: str | None = None
