"""Pipeline artifact value object."""

from dataclasses import dataclass

from engineering_influence.domain.gate import Gate


@dataclass(frozen=True, slots=True)
class Artifact:
    """A durable, typed output produced by a phase."""

    artifact_id: str
    artifact_type: str
    content: str
    gate: Gate

    def __post_init__(self) -> None:
        if not self.artifact_id.strip() or not self.artifact_type.strip():
            raise ValueError("artifact id and type are required")
