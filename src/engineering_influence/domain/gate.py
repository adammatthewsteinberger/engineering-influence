# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Artifact gate value object."""

from dataclasses import dataclass

from engineering_influence.domain.gate_kind import GateKind


@dataclass(frozen=True, slots=True)
class Gate:
    """A typed acceptance gate attached to an artifact."""

    name: str
    kind: GateKind
    rubric: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.rubric.strip():
            raise ValueError("gate name and rubric are required")
