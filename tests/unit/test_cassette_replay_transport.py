# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""CassetteReplayTransport: it answers in order, and only to the request that was recorded."""

from typing import Any

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.cassettes.cassette_redactor import CassetteRedactor
from engineering_influence.infrastructure.cassettes.cassette_replay_transport import (
    CassetteReplayTransport,
)
from engineering_influence.interfaces.cassette_player_interface import CassettePlayerInterface
from engineering_influence.models.cassette import Cassette
from engineering_influence.models.cassette_interaction import CassetteInteraction

URL = "http://provider.test"
KEY = "sk-test-SECRETSECRET"
FIRST = {"model": "m", "prompt": "one"}
SECOND = {"model": "m", "prompt": "two"}


def cassette(*interactions: CassetteInteraction) -> Cassette:
    return Cassette(
        "replay-check",
        "test",
        interactions or (exchange(FIRST, 200, {"n": 1}), exchange(SECOND, 429, {"n": 2})),
    )


def exchange(
    body: Any, status: int, answer: Any, *, path: str = "/v1/messages", method: str = "POST"
) -> CassetteInteraction:
    return CassetteInteraction(method, path, body, status, answer)


def player(*interactions: CassetteInteraction) -> tuple[CassetteReplayTransport, httpx.Client]:
    transport = CassetteReplayTransport(cassette(*interactions), CassetteRedactor([KEY]))
    return transport, httpx.Client(transport=transport)


def refused(call: Any) -> str:
    with pytest.raises(ApplicationError) as error:
        call()
    assert error.value.code == "CASSETTE_MISMATCH"
    assert error.value.http_status == 500
    return error.value.message


def test_it_is_a_cassette_player() -> None:
    transport = CassetteReplayTransport(cassette(), CassetteRedactor())
    assert isinstance(transport, CassettePlayerInterface)


def test_it_replays_status_and_body_in_order_and_counts_what_is_left() -> None:
    transport, client = player()
    assert transport.remaining() == 2
    first = client.post(f"{URL}/v1/messages", json=FIRST)
    assert (first.status_code, first.json()) == (200, {"n": 1})
    assert transport.remaining() == 1
    second = client.post(f"{URL}/v1/messages", json=SECOND)
    assert (second.status_code, second.json()) == (429, {"n": 2})
    assert transport.remaining() == 0
    transport.finish()


def test_a_recorded_answer_of_none_is_an_empty_body() -> None:
    _, client = player(exchange(None, 204, None, method="DELETE", path="/v1/x"))
    reply = client.delete(f"{URL}/v1/x")
    assert (reply.status_code, reply.content) == (204, b"")


def test_a_request_with_no_body_matches_a_recorded_none() -> None:
    _, client = player(exchange(None, 200, {"ok": 1}, method="GET", path="/v1/models"))
    assert client.get(f"{URL}/v1/models").json() == {"ok": 1}


def test_the_query_string_is_part_of_the_path() -> None:
    transport, client = player(exchange(None, 200, {"ok": 1}, method="GET", path="/v1/x?a=1"))
    assert "does not match: the path was /v1/x?a=2" in refused(
        lambda: client.get(f"{URL}/v1/x?a=2")
    )
    assert client.get(f"{URL}/v1/x?a=1").json() == {"ok": 1}
    transport.finish()


def test_a_different_method_path_or_body_is_refused_and_named() -> None:
    _, client = player()
    assert "the method was PUT" in refused(lambda: client.put(f"{URL}/v1/messages", json=FIRST))
    assert "the path was /v1/other" in refused(lambda: client.post(f"{URL}/v1/other", json=FIRST))
    message = refused(
        lambda: client.post(f"{URL}/v1/messages", json={**FIRST, "prompt": "changed"})
    )
    assert message.startswith("request 1 of cassette 'replay-check' (POST /v1/messages)")
    assert "the request body differs in: prompt" in message
    assert "changed" not in message


def test_a_refused_request_does_not_use_up_the_recorded_answer() -> None:
    transport, client = player()
    refused(lambda: client.post(f"{URL}/v1/messages", json={"wrong": True}))
    assert transport.remaining() == 2
    assert client.post(f"{URL}/v1/messages", json=FIRST).json() == {"n": 1}


def test_a_request_after_the_cassette_has_run_out_is_refused() -> None:
    transport, client = player(exchange(FIRST, 200, {"n": 1}))
    client.post(f"{URL}/v1/messages", json=FIRST)
    message = refused(lambda: client.post(f"{URL}/v1/messages", json=FIRST))
    assert "has 1 exchanges and the code asked for another: POST /v1/messages" in message
    assert transport.remaining() == 0


def test_a_body_that_is_not_json_is_refused() -> None:
    _, client = player()
    message = refused(lambda: client.post(f"{URL}/v1/messages", content=b"not json"))
    assert message == "the body of POST /v1/messages is not JSON"


def test_finish_fails_when_the_code_stopped_asking_early() -> None:
    transport, client = player()
    client.post(f"{URL}/v1/messages", json=FIRST)
    assert refused(transport.finish) == (
        "1 of 2 exchanges in cassette 'replay-check' were never replayed"
    )


def test_a_refusal_is_not_an_httpx_error_an_adapter_could_retry() -> None:
    assert not issubclass(ApplicationError, httpx.TransportError)
    _, client = player()
    with pytest.raises(ApplicationError):
        client.post(f"{URL}/v1/other", json=FIRST)


def test_a_request_carrying_the_key_matches_a_cassette_recorded_with_it_masked() -> None:
    recorded = exchange({"prompt": "[REDACTED]"}, 200, {"n": 1}, path="/v1/x?key=[REDACTED]")
    transport, client = player(recorded)
    assert client.post(f"{URL}/v1/x?key={KEY}", json={"prompt": KEY}).json() == {"n": 1}
    transport.finish()


def test_a_refusal_never_prints_the_key() -> None:
    _, client = player()
    for call in (
        lambda: client.post(f"{URL}/v1/other?key={KEY}", json=FIRST),
        lambda: client.post(f"{URL}/v1/messages?key={KEY}", json={"prompt": KEY}),
        lambda: client.post(f"{URL}/v1/messages?key={KEY}", content=b"not json"),
    ):
        message = refused(call)
        assert KEY not in message
        assert "[REDACTED]" in message
