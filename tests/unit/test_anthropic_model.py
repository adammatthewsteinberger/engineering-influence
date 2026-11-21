"""AnthropicModel against recorded-shape replies: request shaping and failure classification."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.models.anthropic_model import AnthropicModel
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.provider_descriptor import ProviderDescriptor

CASSETTES = Path(__file__).parent.parent / "fixtures" / "model_cassettes" / "anthropic"
DESCRIPTOR = ProviderDescriptor(
    provider="anthropic",
    model="claude-test",
    family="claude",
    context_window=200_000,
    max_output_tokens=8_000,
    input_micro_usd_per_mtok=3_000_000,
    output_micro_usd_per_mtok=15_000_000,
    cache_read_micro_usd_per_mtok=300_000,
    cache_write_micro_usd_per_mtok=3_750_000,
    batch_discount_percent=50,
    price_effective="2026-11-01",
    usage_policy_url="https://example.test/policy",
)
REQUEST = ModelRequest(
    system="Be brief.", prompt="Open chapter one.", max_output_tokens=300, prompt_version="v1"
)


def cassette(name: str) -> tuple[int, Any]:
    data = json.loads((CASSETTES / f"{name}.json").read_text())
    return int(data["status"]), data["body"]


class Server:
    """A fake Anthropic: replays cassettes in order and keeps every request it saw."""

    def __init__(self, *names: str) -> None:
        self.names = list(names)
        self.seen: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.seen.append(request)
        status, body = cassette(self.names.pop(0))
        return httpx.Response(status, json=body)

    def model(self, key: str = "sk-test") -> AnthropicModel:
        client = httpx.Client(transport=httpx.MockTransport(self))
        return AnthropicModel(client, key, DESCRIPTOR)


def model_for(handler: Callable[[httpx.Request], httpx.Response]) -> AnthropicModel:
    return AnthropicModel(
        httpx.Client(transport=httpx.MockTransport(handler)), "sk-test", DESCRIPTOR
    )


def test_it_is_a_model_and_reports_its_descriptor() -> None:
    model = Server().model()
    assert isinstance(model, ModelInterface)
    assert model.describe() is DESCRIPTOR
    assert model.availability() is ModelAvailability.AVAILABLE


def test_it_refuses_a_blank_key() -> None:
    with pytest.raises(ValueError, match="API key"):
        Server().model(" ")


def test_complete_sends_the_documented_request_and_maps_the_reply() -> None:
    server = Server("completion")
    response = server.model().complete(REQUEST)

    sent = server.seen[0]
    assert str(sent.url) == "https://api.anthropic.com/v1/messages"
    assert sent.headers["x-api-key"] == "sk-test"
    assert sent.headers["anthropic-version"] == "2023-06-01"
    assert json.loads(sent.content) == {
        "model": "claude-test",
        "max_tokens": 300,
        "system": [{"type": "text", "text": "Be brief.", "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": "Open chapter one."}],
    }
    assert response.text == "Chapter one opens in a harbour."
    assert response.model_snapshot == "claude-test-20261101"
    assert response.stop_reason == "end_turn"
    assert (response.usage.input_tokens, response.usage.output_tokens) == (120, 9)
    assert (response.usage.cache_read_tokens, response.usage.cache_write_tokens) == (0, 2000)


def test_a_cached_prefix_is_billed_at_the_cache_read_rate() -> None:
    server = Server("completion", "completion_cached")
    model = server.model()
    first = model.complete(REQUEST)
    second = model.complete(REQUEST)
    # 2,000 prefix tokens: written once at 3.75/Mtok, then read at 0.30/Mtok.
    assert DESCRIPTOR.cost_micro_usd(second.usage) < DESCRIPTOR.cost_micro_usd(first.usage)
    assert second.usage.cache_read_tokens == 2000


def test_an_empty_system_prompt_is_left_out() -> None:
    server = Server("completion")
    server.model().complete(
        ModelRequest(system="  ", prompt="p", max_output_tokens=5, prompt_version="v1")
    )
    assert "system" not in json.loads(server.seen[0].content)


def test_truncation_and_refusal_are_reported_not_raised() -> None:
    cut = Server("truncated").model().complete(REQUEST)
    refused = Server("refusal").model().complete(REQUEST)
    assert cut.was_truncated() and cut.text == "It was a dark and"
    assert refused.was_refused() and refused.text == ""


def test_count_tokens_posts_without_an_output_cap() -> None:
    server = Server("count_tokens")
    assert server.model().count_tokens(REQUEST) == 2120
    assert str(server.seen[0].url) == "https://api.anthropic.com/v1/messages/count_tokens"
    assert "max_tokens" not in json.loads(server.seen[0].content)


def test_a_spent_credit_balance_parks_the_run_and_the_model_reports_it() -> None:
    model = Server("error_credit", "completion").model()
    with pytest.raises(CapacityExhaustedError, match="credit is exhausted"):
        model.complete(REQUEST)
    assert model.availability() is ModelAvailability.CREDITS_EXHAUSTED
    model.complete(REQUEST)
    assert model.availability() is ModelAvailability.AVAILABLE


def test_a_billing_status_402_also_means_credit() -> None:
    model = model_for(
        lambda r: httpx.Response(402, json={"error": {"type": "billing_error", "message": "pay"}})
    )
    with pytest.raises(CapacityExhaustedError):
        model.complete(REQUEST)
    assert model.availability() is ModelAvailability.CREDITS_EXHAUSTED


@pytest.mark.parametrize("status", [401, 403])
def test_a_refused_key_is_an_authentication_failure(status: int) -> None:
    model = model_for(
        lambda r: httpx.Response(
            status, json={"error": {"type": "authentication_error", "message": "bad"}}
        )
    )
    with pytest.raises(CapacityExhaustedError, match="refused the API key"):
        model.complete(REQUEST)
    assert model.availability() is ModelAvailability.AUTHENTICATION_FAILED


@pytest.mark.parametrize("name", ["error_rate", "error_overloaded"])
def test_rate_limits_and_server_errors_are_transient(name: str) -> None:
    with pytest.raises(TransientStageError):
        Server(name).model().complete(REQUEST)


def test_an_unplayable_request_is_not_retried() -> None:
    with pytest.raises(ApplicationError) as caught:
        Server("error_invalid").model().complete(REQUEST)
    assert caught.value.code == "MODEL_REJECTED"
    assert "max_tokens" in caught.value.message


def test_a_dropped_connection_and_a_timeout_are_transient() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route")

    def stall(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    for handler in (refuse, stall):
        with pytest.raises(TransientStageError, match="could not be reached"):
            model_for(handler).complete(REQUEST)


def test_an_error_without_a_json_body_still_names_the_status() -> None:
    model = model_for(lambda r: httpx.Response(400, text="<html>gateway</html>"))
    with pytest.raises(ApplicationError, match="400, unknown"):
        model.complete(REQUEST)


@pytest.mark.parametrize(
    "body",
    [
        {"content": [], "usage": {"input_tokens": 1, "output_tokens": 1}, "model": "m"},
        {
            "content": [],
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "stop_reason": "tool_use",
            "model": "m",
        },
        {"content": [{"type": "text", "text": "x"}], "stop_reason": "end_turn", "model": "m"},
        {
            "content": [{"type": "text", "text": "x"}],
            "usage": {"input_tokens": "many", "output_tokens": 1},
            "stop_reason": "end_turn",
            "model": "m",
        },
    ],
)
def test_a_reply_it_cannot_read_is_an_unexpected_response(body: dict[str, Any]) -> None:
    model = model_for(lambda r: httpx.Response(200, json=body))
    with pytest.raises(ApplicationError) as caught:
        model.complete(REQUEST)
    assert caught.value.code == "MODEL_RESPONSE_UNEXPECTED"


def test_a_token_count_it_cannot_read_is_an_unexpected_response() -> None:
    model = model_for(lambda r: httpx.Response(200, json={"tokens": 5}))
    with pytest.raises(ApplicationError) as caught:
        model.count_tokens(REQUEST)
    assert caught.value.code == "MODEL_RESPONSE_UNEXPECTED"


@pytest.mark.parametrize("payload", [b"not json", b"[1, 2]"])
def test_a_success_body_that_is_not_an_object_is_unexpected(payload: bytes) -> None:
    model = model_for(lambda r: httpx.Response(200, content=payload))
    with pytest.raises(ApplicationError) as caught:
        model.complete(REQUEST)
    assert caught.value.code == "MODEL_RESPONSE_UNEXPECTED"


def test_the_key_never_appears_in_an_error() -> None:
    model = model_for(
        lambda r: httpx.Response(
            401, json={"error": {"type": "authentication_error", "message": "bad"}}
        )
    )
    with pytest.raises(CapacityExhaustedError) as caught:
        model.complete(REQUEST)
    assert "sk-test" not in str(caught.value)


@pytest.mark.parametrize("status", [500, 502, 503, 529])
def test_every_server_error_status_is_transient(status: int) -> None:
    model = model_for(
        lambda r: httpx.Response(status, json={"error": {"type": "api_error", "message": "boom"}})
    )
    with pytest.raises(TransientStageError):
        model.complete(REQUEST)


def test_a_client_error_just_below_the_server_range_is_not_transient() -> None:
    model = model_for(
        lambda r: httpx.Response(499, json={"error": {"type": "x", "message": "odd"}})
    )
    with pytest.raises(ApplicationError):
        model.complete(REQUEST)
