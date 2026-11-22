# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""PinnedTarget and PinDecision: where a request really goes, or why it does not."""

import dataclasses

import pytest

from engineering_influence.models.interfaces.pin_decision_interface import PinDecisionInterface
from engineering_influence.models.interfaces.pinned_target_interface import PinnedTargetInterface
from engineering_influence.models.pin_decision import PinDecision
from engineering_influence.models.pinned_target import PinnedTarget


def test_a_target_says_where_to_connect_and_whom_to_ask_for() -> None:
    target = PinnedTarget("https://93.184.216.34/x", "bees.example", "bees.example")
    assert isinstance(target, PinnedTargetInterface)
    assert target.request_headers() == {"host": "bees.example"}
    assert target.request_extensions() == {"sni_hostname": "bees.example"}


def test_a_target_for_an_address_has_no_name_to_verify() -> None:
    target = PinnedTarget("https://93.184.216.34/x", "93.184.216.34")
    assert target.sni_hostname == "" and target.request_extensions() == {}


@pytest.mark.parametrize("fields", [("", "h"), ("https://1.2.3.4/", "")])
def test_a_target_needs_an_address_and_a_host(fields: tuple[str, str]) -> None:
    with pytest.raises(ValueError, match="address to connect to and a host to ask for"):
        PinnedTarget(*fields)


def test_a_target_cannot_be_changed() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        PinnedTarget("https://1.2.3.4/", "h").url = "https://5.6.7.8/"  # type: ignore[misc]


def test_a_decision_is_a_target_or_a_reason() -> None:
    target = PinnedTarget("https://1.2.3.4/", "h")
    go, stop = PinDecision.pinned(target), PinDecision.refused("non_public_address")
    assert isinstance(go, PinDecisionInterface)
    assert (go.target, go.reason) == (target, "")
    assert (stop.target, stop.reason) == (None, "non_public_address")


def test_a_decision_with_both_or_neither_is_refused() -> None:
    with pytest.raises(ValueError, match="a target to connect to, or a reason for refusing"):
        PinDecision(PinnedTarget("https://1.2.3.4/", "h"), "why")
    with pytest.raises(ValueError, match="a target to connect to, or a reason for refusing"):
        PinDecision()
