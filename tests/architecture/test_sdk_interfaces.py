"""The SDK is a separate distribution, but its clients follow the same interface rules."""

import inspect

import engineering_influence_sdk
import pytest
from architecture_metrics import REPO, ArchitectureMetrics
from engineering_influence_sdk import AsyncEngineeringInfluenceClient, EngineeringInfluenceClient
from engineering_influence_sdk.interfaces.async_client_interface import (
    AsyncEngineeringInfluenceClientInterface,
)
from engineering_influence_sdk.interfaces.client_interface import (
    EngineeringInfluenceClientInterface,
)

SDK = REPO / "packages" / "engineering-influence-sdk" / "src" / "engineering_influence_sdk"


@pytest.mark.parametrize(
    "rule",
    [
        "classes_without_an_interface",
        "folders_without_an_interfaces_folder",
        "interface_files_not_paired",
        "interface_rule_breaks",
    ],
)
def test_the_sdk_obeys_every_interface_rule(rule: str) -> None:
    assert getattr(ArchitectureMetrics(SDK), rule)() == 0


def test_the_sdk_public_surface_is_unchanged() -> None:
    assert engineering_influence_sdk.__all__ == [
        "AsyncEngineeringInfluenceClient",
        "EngineeringInfluenceClient",
    ]


@pytest.mark.parametrize(
    ("client", "interface"),
    [
        (EngineeringInfluenceClient, EngineeringInfluenceClientInterface),
        (AsyncEngineeringInfluenceClient, AsyncEngineeringInfluenceClientInterface),
    ],
)
def test_each_client_implements_its_interface_with_the_same_signatures(
    client: type, interface: type
) -> None:
    assert issubclass(client, interface)
    for name in ("start_pipeline", "close"):
        assert inspect.signature(getattr(client, name)) == inspect.signature(
            getattr(interface, name)
        )
        assert inspect.iscoroutinefunction(getattr(client, name)) == inspect.iscoroutinefunction(
            getattr(interface, name)
        )
