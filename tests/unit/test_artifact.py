"""Tests for typed artifacts and gates."""

from engineering_influence.domain import Artifact, Gate, GateKind


def test_artifact_keeps_gate_kind_and_rubric() -> None:
    artifact = Artifact(
        "a1",
        "thick_thesis",
        "A falsifiable thesis.",
        Gate("thesis-thick", GateKind.AUTO, "Check falsifiability and source coverage."),
    )
    assert artifact.gate.kind is GateKind.AUTO
