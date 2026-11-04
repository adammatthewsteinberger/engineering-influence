# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Path confinement and filename sanitising."""

from pathlib import Path

from vibey_bootstrap.path_safety import confine_to_root, sanitize_path_segment

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.path_guard_port import PathGuardPort


class ConfinedPathGuard(PathGuardPort):
    """Resolve caller paths against a root and refuse any that leave it."""

    def confine(self, raw: str | Path, root: Path) -> Path:
        """Return the resolved path inside root.

        Relative input is joined onto root first: the underlying helper would
        otherwise resolve it against the process working directory.
        """
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            return confine_to_root(candidate, allowed_root=root)
        except ValueError as error:
            raise ApplicationError(
                code="PATH_ESCAPE", message="path is outside the permitted directory"
            ) from error

    def segment(self, value: str) -> str:
        """Return one safe path component."""
        return sanitize_path_segment(value)
