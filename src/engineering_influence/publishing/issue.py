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
