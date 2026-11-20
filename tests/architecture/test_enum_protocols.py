"""Enums cannot inherit an ABC, so each has a runtime-checkable Protocol; check them against it."""

import importlib
import tomllib
from enum import Enum
from typing import Any

import pytest
from architecture_metrics import REPO

ENUMS = [
    entry
    for entry in tomllib.loads((REPO / "scripts/refactor/move_map.toml").read_text())["class"]
    if entry["kind"] == "enum"
]


def load(module: str, name: str) -> Any:
    return getattr(importlib.import_module(module), name)


def test_the_map_lists_the_enums_this_test_covers() -> None:
    assert {e["new_name"] for e in ENUMS} == {
        "AdvanceOutcome",
        "BookKind",
        "FailureKind",
        "GateKind",
        "JobOutcome",
        "PhaseState",
        "PipelineStage",
        "RunStatus",
    }


@pytest.mark.parametrize("entry", ENUMS, ids=lambda e: e["new_name"])
def test_every_member_of_the_enum_satisfies_its_protocol(entry: dict[str, Any]) -> None:
    enum = load(entry["new"], entry["new_name"])
    protocol = load(entry["interface_module"], entry["interface"])

    assert issubclass(enum, Enum)
    assert getattr(protocol, "_is_runtime_protocol", False), (
        "the protocol must be runtime_checkable"
    )
    assert all(isinstance(member, protocol) for member in enum)
    assert not isinstance(object(), protocol)
