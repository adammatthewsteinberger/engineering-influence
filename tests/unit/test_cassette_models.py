# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Cassette and CassetteInteraction: what they refuse, and how a request is compared."""

from typing import Any

import pytest

from engineering_influence.models.cassette import Cassette
from engineering_influence.models.cassette_interaction import CassetteInteraction

BODY = {"model": "m", "max_tokens": 10}


def interaction(**changes: Any) -> CassetteInteraction:
    values: dict[str, Any] = {
        "method": "POST",
        "path": "/v1/messages",
        "request_body": BODY,
        "status": 200,
        "response_body": {"ok": True},
    }
    values.update(changes)
    return CassetteInteraction(**values)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"method": "post"}, "upper-case"),
        ({"method": ""}, "upper-case"),
        ({"method": "PO ST"}, "upper-case"),
        ({"path": "v1/messages"}, "starts with"),
        ({"status": 99}, "between 100 and 599"),
        ({"status": 600}, "between 100 and 599"),
    ],
)
def test_an_interaction_refuses_what_could_not_have_happened(
    changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        interaction(**changes)


@pytest.mark.parametrize("status", [100, 200, 599])
def test_an_interaction_accepts_the_ends_of_the_status_range(status: int) -> None:
    assert interaction(status=status).status == status


def test_the_recorded_request_does_not_mismatch() -> None:
    assert interaction().mismatch("POST", "/v1/messages", dict(BODY)) == ""


def test_key_order_in_a_body_is_not_a_difference() -> None:
    assert interaction().mismatch("POST", "/v1/messages", {"max_tokens": 10, "model": "m"}) == ""


def test_a_different_method_or_path_is_named_with_both_values() -> None:
    assert interaction().mismatch("GET", "/v1/messages", BODY) == (
        "the method was GET, the cassette has POST"
    )
    assert interaction().mismatch("POST", "/v1/other", BODY) == (
        "the path was /v1/other, the cassette has /v1/messages"
    )


def test_a_different_body_is_described_by_key_names_never_values() -> None:
    message = interaction().mismatch(
        "POST", "/v1/messages", {"model": "m", "max_tokens": 9999, "extra": "hunter2"}
    )
    assert message == "the request body differs in: extra, max_tokens"
    assert "9999" not in message
    assert "hunter2" not in message


def test_a_missing_key_is_not_the_same_as_a_key_set_to_none() -> None:
    recorded = interaction(request_body={"a": None})
    assert recorded.mismatch("POST", "/v1/messages", {}) == "the request body differs in: a"
    assert recorded.mismatch("POST", "/v1/messages", {"a": None}) == ""


def test_bodies_that_are_not_both_objects_differ_without_naming_keys() -> None:
    assert interaction().mismatch("POST", "/v1/messages", None) == "the request body differs"
    assert interaction(request_body=[1]).mismatch("POST", "/v1/messages", [2]) == (
        "the request body differs"
    )
    assert interaction(request_body=None).mismatch("POST", "/v1/messages", {"a": 1}) == (
        "the request body differs"
    )


def test_a_body_of_none_matches_a_recorded_none() -> None:
    assert interaction(request_body=None).mismatch("POST", "/v1/messages", None) == ""


def cassette(**changes: Any) -> Cassette:
    values: dict[str, Any] = {
        "name": "anthropic-chapter-one",
        "provider": "anthropic",
        "interactions": (interaction(), interaction(status=429)),
    }
    values.update(changes)
    return Cassette(**values)


@pytest.mark.parametrize(
    "name", ["", "Upper", "has space", "-lead", "_lead", "a/b", "../x", "dot.json", "a\n"]
)
def test_a_cassette_refuses_a_name_that_is_not_a_plain_file_name(name: str) -> None:
    with pytest.raises(ValueError, match="not a cassette name"):
        cassette(name=name)


@pytest.mark.parametrize("name", ["a", "0", "anthropic-chapter-one", "a_b-c9"])
def test_a_cassette_accepts_a_plain_name(name: str) -> None:
    assert cassette(name=name).name == name


def test_a_cassette_names_its_provider() -> None:
    with pytest.raises(ValueError, match="names its provider"):
        cassette(provider="  ")


@pytest.mark.parametrize("interactions", [(), [interaction()]])
def test_a_cassette_holds_a_tuple_of_at_least_one_interaction(interactions: Any) -> None:
    with pytest.raises(ValueError, match="at least one interaction"):
        cassette(interactions=interactions)


def test_interactions_are_read_by_position_and_run_out() -> None:
    held = cassette()
    assert held.interaction_at(0) is held.interactions[0]
    assert held.interaction_at(1) is held.interactions[1]
    assert held.interaction_at(2) is None
    assert held.interaction_at(-1) is None
