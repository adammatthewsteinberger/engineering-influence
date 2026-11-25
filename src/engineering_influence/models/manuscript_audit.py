# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What the manuscript audit and the release readiness check said about an assembled book."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.manuscript_audit_interface import (
    ManuscriptAuditInterface,
)


@dataclass(frozen=True, slots=True)
class ManuscriptAudit(ManuscriptAuditInterface):
    """Whether the book passed, what was wrong with it, and the reports that say so.

    ``errors`` are what stops a release; ``warnings`` are what the author should look at (a missing price, for
    one) and do not. ``files`` are the report files as ``(name, bytes)`` pairs, with plain names such as
    ``release-readiness.json``.
    """

    passed: bool
    status: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    files: tuple[tuple[str, bytes], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.passed, bool) or not self.status.strip():
            raise ValueError("an audit says whether it passed and in what status")
        for label, values in (("errors", self.errors), ("warnings", self.warnings)):
            if not isinstance(values, tuple) or any(not text.strip() for text in values):
                raise ValueError(f"the {label} are a tuple of messages")
        names = [name for name, _ in self.files]
        if not isinstance(self.files, tuple) or len(set(names)) != len(names):
            raise ValueError("the report files are a tuple of distinct names")
        if any(not name or "/" in name or name.startswith(".") for name in names):
            raise ValueError("a report file has a plain name, with no folder in it")
        if self.passed and self.errors:
            raise ValueError("an audit with errors did not pass")
