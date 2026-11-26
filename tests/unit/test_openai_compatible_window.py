# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The adapter refuses a prompt its model's window cannot hold before anything is sent, and sends one it can hold."""

import json

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.models.openai_compatible_model import (
    OpenAICompatibleModel,
)
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.provider_descriptor import ProviderDescriptor

WINDOW = ProviderDescriptor(
    provider="local",
    model="window-test",
    family="test",
    context_window=1_000,
    max_output_tokens=100,
    input_micro_usd_per_mtok=0,
    output_micro_usd_per_mtok=0,
    cache_read_micro_usd_per_mtok=0,
    cache_write_micro_usd_per_mtok=0,
    batch_discount_percent=0,
    price_effective="2026-11-01",
    usage_policy_url="https://example.test/policy",
)
REPLY = {
    "id": "r1",
    "model": "window-test",
    "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
}


def adapter(seen: list[httpx.Request]) -> OpenAICompatibleModel:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=REPLY)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAICompatibleModel(client, "key", WINDOW, base_url="http://local.test")


def test_a_prompt_the_window_cannot_hold_is_refused_before_anything_is_sent() -> None:
    seen: list[httpx.Request] = []
    request = ModelRequest(
        system="Be brief.", prompt="x" * 6_000, max_output_tokens=100, prompt_version="v1"
    )
    with pytest.raises(ApplicationError) as refused:
        adapter(seen).complete(request)
    assert refused.value.code == "CONTEXT_TOO_LARGE"
    assert "window of 1000 tokens" in refused.value.message
    assert seen == []


def test_a_prompt_the_window_can_hold_is_sent() -> None:
    seen: list[httpx.Request] = []
    request = ModelRequest(
        system="Be brief.", prompt="Open chapter one.", max_output_tokens=100, prompt_version="v1"
    )
    adapter(seen).complete(request)
    assert len(seen) == 1
    assert json.loads(seen[0].content)["max_tokens"] == 100
