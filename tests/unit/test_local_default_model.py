"""The free local default, and the reasoning effort a profile may ask a local server for."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.models.openai_compatible_model import (
    OpenAICompatibleModel,
)
from engineering_influence.infrastructure.models.toml_model_profile_loader import (
    TomlModelProfileLoader,
)
from engineering_influence.models.model_profile import ModelProfile
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.services.local_default_model import LocalDefaultModel


def test_the_default_is_gpt_oss_on_ollama_at_no_cost() -> None:
    free = LocalDefaultModel({})
    profile, descriptor = free.profile(), free.descriptor()
    assert (profile.name, profile.adapter, profile.provider, profile.model) == (
        "local-default",
        "openai_compatible",
        "local",
        "gpt-oss:20b",
    )
    assert (profile.base_url, profile.api_key_env, profile.reasoning_effort) == (
        "http://127.0.0.1:11434",
        "",
        "low",
    )
    assert not profile.requires_key()
    assert (descriptor.provider, descriptor.model) == ("local", "gpt-oss:20b")
    assert (descriptor.context_window, descriptor.max_output_tokens) == (32_768, 8_192)
    assert descriptor.usage_policy_url == "https://huggingface.co/openai/gpt-oss-20b"
    assert descriptor.price_effective == "2026-01-01"


def test_nothing_the_default_costs_is_ever_charged() -> None:
    descriptor = LocalDefaultModel({}).descriptor()
    assert (
        descriptor.input_micro_usd_per_mtok,
        descriptor.output_micro_usd_per_mtok,
        descriptor.cache_read_micro_usd_per_mtok,
        descriptor.cache_write_micro_usd_per_mtok,
        descriptor.batch_discount_percent,
    ) == (0, 0, 0, 0, 0)
    assert descriptor.worst_case_micro_usd(30_000, 8_000) == 0


def test_the_model_and_the_server_may_be_named_and_are_trimmed() -> None:
    free = LocalDefaultModel(
        {"EI_LOCAL_MODEL": " qwen3:14b ", "EI_LOCAL_URL": " http://127.0.0.1:8080 "}
    )
    assert (free.profile().model, free.profile().base_url) == ("qwen3:14b", "http://127.0.0.1:8080")
    assert free.descriptor().model == "qwen3:14b"


def test_blank_settings_mean_the_defaults() -> None:
    free = LocalDefaultModel({"EI_LOCAL_MODEL": "  ", "EI_LOCAL_URL": ""})
    assert (free.profile().model, free.profile().base_url) == (
        "gpt-oss:20b",
        "http://127.0.0.1:11434",
    )


def test_a_setting_that_cannot_be_used_is_refused_by_name() -> None:
    with pytest.raises(ApplicationError) as caught:
        LocalDefaultModel({"EI_LOCAL_URL": "ftp://example.test"}).profile()
    assert (caught.value.code, caught.value.http_status) == ("STAGE_LOCAL_MODEL_INVALID", 503)
    assert "EI_LOCAL_MODEL or EI_LOCAL_URL" in caught.value.message


def profile(**changes: Any) -> ModelProfile:
    values: dict[str, Any] = {
        "name": "p",
        "adapter": "openai_compatible",
        "provider": "local",
        "model": "m",
        "base_url": "http://127.0.0.1:1",
    }
    values.update(changes)
    return ModelProfile(**values)


@pytest.mark.parametrize("effort", ["low", "medium", "high"])
def test_a_profile_may_ask_for_each_reasoning_effort(effort: str) -> None:
    assert profile(reasoning_effort=effort).reasoning_effort == effort


def test_a_profile_asks_for_none_by_default() -> None:
    assert profile().reasoning_effort == ""


def test_a_reasoning_effort_outside_the_list_is_refused() -> None:
    with pytest.raises(ValueError, match="reasoning_effort must be one of low, medium, high"):
        profile(reasoning_effort="extreme")


def test_only_an_openai_compatible_profile_may_ask_for_one() -> None:
    with pytest.raises(ValueError, match="applies to an openai_compatible profile"):
        profile(adapter="anthropic", api_key_env="K", reasoning_effort="low")


def test_the_profile_file_reads_a_reasoning_effort(tmp_path: Path) -> None:
    path = tmp_path / "profiles.toml"
    path.write_text(
        '[[profile]]\nname = "p"\nadapter = "openai_compatible"\nprovider = "local"\n'
        'model = "m"\nbase_url = "http://127.0.0.1:1"\nreasoning_effort = "medium"\n'
    )
    assert TomlModelProfileLoader().load(path)[0].reasoning_effort == "medium"


def sent_body(effort: str) -> dict[str, Any]:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "m",
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1},
            },
        )

    free = LocalDefaultModel({})
    client = httpx.Client(transport=httpx.MockTransport(handler))
    model = OpenAICompatibleModel(
        client, "", free.descriptor(), free.profile().base_url, "max_tokens", effort
    )
    model.complete(
        ModelRequest(system="", prompt="Hello.", max_output_tokens=50, prompt_version="v1")
    )
    return seen[0]


def test_the_adapter_sends_a_reasoning_effort_only_when_it_has_one() -> None:
    assert sent_body("low")["reasoning_effort"] == "low"
    assert "reasoning_effort" not in sent_body("")
