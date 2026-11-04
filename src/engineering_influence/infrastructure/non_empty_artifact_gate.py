# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A placeholder automatic gate that checks only that something was produced."""

from engineering_influence.domain.artifact import Artifact
from engineering_influence.interfaces.gate_port import GatePort


class NonEmptyArtifactGate(GatePort):
    """Accepts any artifact with non-blank content.

    A real automatic gate scores the artifact against its rubric; this one exists so the
    pipeline can advance without a model.
    """

    def evaluate(self, artifact: Artifact) -> bool:
        """Return whether the artifact has content."""
        return bool(artifact.content.strip())
