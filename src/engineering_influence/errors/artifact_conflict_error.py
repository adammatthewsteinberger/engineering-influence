# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An artifact name that already holds different bytes."""

from engineering_influence.errors.interfaces.artifact_conflict_error_interface import (
    ArtifactConflictErrorInterface,
)


class ArtifactConflictError(ArtifactConflictErrorInterface, ValueError):
    """Raised when a run stores different bytes under a name it already used.

    Artifacts are write-once. Storing the same bytes again is fine; different bytes mean a
    stage was not deterministic, and replacing the file would hide that.
    """
