"""OpenAICompatibleModel against documented-shape replies: request shaping and failure sorting."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.models.openai_compatible_model import (
    OpenAICompatibleModel,
)
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor

CASSETTES = Path(__file__).parent.parent / "fixtures" / "model_cassettes" / "openai_compatible"
DESCRIPTOR = ProviderDescriptor(
    provider="openai",
    model="gpt-test",
    family="gpt",
    context_window=128_000,
    max_output_tokens=16_000,
    input_micro_usd_per_mtok=2_500_000,
    output_micro_usd_per_mtok=10_000_000,
    cache_read_micro_usd_per_mtok=1_250_000,
    cache_write_micro_usd_per_mtok=2_500_000,
    batch_discount_percent=50,
    price_effective="2026-11-01",
    usage_policy_url="https://example.test/policy",
)
REQUEST = ModelRequest(
    system="Be brief.", prompt="Open chapter one.", max_output_tokens=300, prompt_version="v1"
)
ERROR_BODY = {"error": {"message": "boom", "type": "server_error", "code": None}}


class Server:
    """A fake server: replays cassettes in order and keeps every request it saw."""

    def __init__(self, *names: str) -> None:
        self.names = list(names)
        self.seen: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.seen.append(request)
        data = json.loads((CASSETTES / f"{self.names.pop(0)}.json").read_text())
        return httpx.Response(int(data["status"]), json=data["body"])

    def model(self, key: str = "sk-test", **options: str) -> OpenAICompatibleModel:
        client = httpx.Client(transport=httpx.MockTransport(self))
        return OpenAICompatibleModel(client, key, DESCRIPTOR, **options)


def model_for(handler: Callable[[httpx.Request], httpx.Response]) -> OpenAICompatibleModel:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAICompatibleModel(client, "sk-test", DESCRIPTOR)


def test_it_is_a_model_and_reports_its_descriptor() -> None:
    model = Server().model()
    assert isinstance(model, ModelInterface)
    assert model.describe() is DESCRIPTOR
    assert model.availability() is ModelAvailability.AVAILABLE


def test_complete_sends_the_chat_completions_request_and_maps_the_reply() -> None:
    server = Server("completion")
    response = server.model().complete(REQUEST)

    sent = server.seen[0]
    assert str(sent.url) == "https://api.openai.com/v1/chat/completions"
    assert sent.headers["authorization"] == "Bearer sk-test"
    assert json.loads(sent.content) == {
        "model": "gpt-test",
        "max_tokens": 300,
        "messages": [
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": "Open chapter one."},
        ],
    }
    assert response.text == "Chapter one opens in a harbour."
    assert response.model_snapshot == "gpt-test-2026-11-01"
    assert response.stop_reason == "end_turn"
    assert (response.usage.input_tokens, response.usage.output_tokens) == (120, 9)
    assert (response.usage.cache_read_tokens, response.usage.cache_write_tokens) == (0, 0)


def test_openai_proper_can_name_its_own_output_cap_field() -> None:
    server = Server("completion")
    server.model(output_cap_field="max_completion_tokens").complete(REQUEST)
    body = json.loads(server.seen[0].content)
    assert body["max_completion_tokens"] == 300
    assert "max_tokens" not in body


def test_a_local_server_needs_no_key_and_gets_no_authorization_header() -> None:
    server = Server("completion")
    server.model(key="  ", base_url="http://localhost:11434/").complete(REQUEST)
    assert str(server.seen[0].url) == "http://localhost:11434/v1/chat/completions"
    assert "authorization" not in server.seen[0].headers


def test_an_empty_system_prompt_is_left_out() -> None:
    server = Server("completion")
    request = ModelRequest(system=" ", prompt="p", max_output_tokens=5, prompt_version="v1")
    server.model().complete(request)
    assert [m["role"] for m in json.loads(server.seen[0].content)["messages"]] == ["user"]


def test_cached_prompt_tokens_are_split_out_and_priced_at_the_cache_rate() -> None:
    model = Server("completion", "completion_cached").model()
    first = model.complete(REQUEST)
    second = model.complete(REQUEST)
    assert (second.usage.input_tokens, second.usage.cache_read_tokens) == (50, 2000)
    # 50 fresh x 2.5 + 3 out x 10 + 2,000 cached x 1.25 = 125 + 30 + 2,500 micro-USD per 1M-token unit.
    assert DESCRIPTOR.cost_micro_usd(second.usage) == 2655
    assert DESCRIPTOR.cost_micro_usd(second.usage) < DESCRIPTOR.cost_micro_usd(ModelUsage(2050, 3))
    assert first.usage.cache_read_tokens == 0


def test_truncation_and_every_form_of_refusal_are_reported_not_raised() -> None:
    cut = Server("truncated").model().complete(REQUEST)
    refused = Server("refusal").model().complete(REQUEST)
    filtered = Server("content_filter").model().complete(REQUEST)
    assert cut.was_truncated() and cut.text == "It was a dark and"
    assert refused.was_refused() and refused.text == ""
    assert filtered.was_refused()


def test_the_token_count_is_a_byte_upper_bound_plus_template_overhead() -> None:
    model = Server().model()
    # "Be brief." (9 bytes) + "Open chapter one." (17 bytes) + 2 messages x 8 tokens of overhead.
    assert model.count_tokens(REQUEST) == 9 + 17 + 16
    assert (
        model.count_tokens(
            ModelRequest(system="", prompt="é", max_output_tokens=5, prompt_version="v1")
        )
        == 2 + 8
    )


def test_spent_quota_parks_the_run_and_the_model_reports_it() -> None:
    model = Server("error_quota", "completion").model()
    with pytest.raises(CapacityExhaustedError, match="out of credit"):
        model.complete(REQUEST)
    assert model.availability() is ModelAvailability.CREDITS_EXHAUSTED
    model.complete(REQUEST)
    assert model.availability() is ModelAvailability.AVAILABLE


def test_a_billing_status_402_also_means_credit() -> None:
    model = model_for(lambda r: httpx.Response(402, json=ERROR_BODY))
    with pytest.raises(CapacityExhaustedError):
        model.complete(REQUEST)
    assert model.availability() is ModelAvailability.CREDITS_EXHAUSTED


@pytest.mark.parametrize("status", [401, 403])
def test_a_refused_key_is_an_authentication_failure(status: int) -> None:
    model = model_for(lambda r: httpx.Response(status, json=ERROR_BODY))
    with pytest.raises(CapacityExhaustedError, match="refused the API key"):
        model.complete(REQUEST)
    assert model.availability() is ModelAvailability.AUTHENTICATION_FAILED


@pytest.mark.parametrize("name", ["error_rate", "error_server"])
def test_rate_limits_and_server_errors_are_transient(name: str) -> None:
    with pytest.raises(TransientStageError):
        Server(name).model().complete(REQUEST)


@pytest.mark.parametrize("status", [408, 500, 502, 503, 529])
def test_every_timeout_and_server_status_is_transient(status: int) -> None:
    model = model_for(lambda r: httpx.Response(status, json=ERROR_BODY))
    with pytest.raises(TransientStageError):
        model.complete(REQUEST)


@pytest.mark.parametrize("status", [400, 404, 409, 499])
def test_other_client_errors_are_not_retried(status: int) -> None:
    model = model_for(lambda r: httpx.Response(status, json=ERROR_BODY))
    with pytest.raises(ApplicationError) as caught:
        model.complete(REQUEST)
    assert caught.value.code == "MODEL_REJECTED"


def test_a_context_overflow_is_rejected_with_its_reason() -> None:
    with pytest.raises(ApplicationError, match="context_length_exceeded"):
        Server("error_context").model().complete(REQUEST)


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


def choice(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": "m",
        "choices": [{"message": {"content": "x"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1},
    }
    body.update(changes)
    return body


@pytest.mark.parametrize(
    "body",
    [
        choice(choices=[]),
        choice(choices=[{"message": {"content": "x"}, "finish_reason": "function_call"}]),
        choice(usage=None),
        choice(usage={"prompt_tokens": "many", "completion_tokens": 1}),
        {"model": "m"},
    ],
)
def test_a_reply_it_cannot_read_is_an_unexpected_response(body: dict[str, Any]) -> None:
    model = model_for(lambda r: httpx.Response(200, json=body))
    with pytest.raises(ApplicationError) as caught:
        model.complete(REQUEST)
    assert caught.value.code == "MODEL_RESPONSE_UNEXPECTED"


@pytest.mark.parametrize("payload", [b"not json", b"[1, 2]"])
def test_a_success_body_that_is_not_an_object_is_unexpected(payload: bytes) -> None:
    model = model_for(lambda r: httpx.Response(200, content=payload))
    with pytest.raises(ApplicationError) as caught:
        model.complete(REQUEST)
    assert caught.value.code == "MODEL_RESPONSE_UNEXPECTED"


def test_the_key_never_appears_in_an_error() -> None:
    model = model_for(lambda r: httpx.Response(401, json=ERROR_BODY))
    with pytest.raises(CapacityExhaustedError) as caught:
        model.complete(REQUEST)
    assert "sk-test" not in str(caught.value)
