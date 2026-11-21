# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Record an adapter's calls once, then replay them: the adapter cannot tell, and cannot be misled."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.cassettes.cassette_recording_transport import (
    CassetteRecordingTransport,
)
from engineering_influence.infrastructure.cassettes.cassette_redactor import CassetteRedactor
from engineering_influence.infrastructure.cassettes.cassette_replay_transport import (
    CassetteReplayTransport,
)
from engineering_influence.infrastructure.cassettes.json_cassette_store import JsonCassetteStore
from engineering_influence.infrastructure.models.anthropic_model import AnthropicModel
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.provider_descriptor import ProviderDescriptor

FIXTURES = Path(__file__).parent.parent / "fixtures" / "model_cassettes" / "anthropic"
KEY = "sk-test-SECRETSECRET"
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


def provider_answering(*names: str, echo_key: bool = False) -> httpx.MockTransport:
    """A stand-in for Anthropic that answers from the hand-written fixtures, in order."""
    remaining = list(names)

    def answer(request: httpx.Request) -> httpx.Response:
        data = json.loads((FIXTURES / f"{remaining.pop(0)}.json").read_text())
        body: Any = data["body"]
        if echo_key:
            body = json.loads(json.dumps(body).replace("invalid x-api-key", f"bad key {KEY}"))
        return httpx.Response(int(data["status"]), json=body)

    return httpx.MockTransport(answer)


def model_over(transport: httpx.BaseTransport) -> AnthropicModel:
    return AnthropicModel(httpx.Client(transport=transport), KEY, DESCRIPTOR)


def record(
    tmp_path: Path, provider: httpx.MockTransport, calls: Any, name: str
) -> JsonCassetteStore:
    store = JsonCassetteStore(tmp_path, CassetteRedactor([KEY]))
    transport = CassetteRecordingTransport(provider, CassetteRedactor([KEY]), store)
    try:
        calls(model_over(transport))
    except (CapacityExhaustedError, TransientStageError):
        pass
    transport.finish(name, "anthropic", "synthetic brief; fixtures stand in for the provider")
    return store


def test_a_replayed_call_gives_the_adapter_the_same_answer_as_the_recorded_one(
    tmp_path: Path,
) -> None:
    seen: list[Any] = []
    store = record(
        tmp_path,
        provider_answering("count_tokens", "completion"),
        lambda model: seen.extend([model.count_tokens(REQUEST), model.complete(REQUEST)]),
        "chapter-one",
    )
    replay = CassetteReplayTransport(store.load("chapter-one"), CassetteRedactor([KEY]))
    model = model_over(replay)
    assert [model.count_tokens(REQUEST), model.complete(REQUEST)] == seen
    replay.finish()
    assert KEY not in (tmp_path / "chapter-one.json").read_text(encoding="utf-8")


def test_a_prompt_that_changed_since_the_recording_fails_loudly_and_is_not_retried(
    tmp_path: Path,
) -> None:
    store = record(
        tmp_path, provider_answering("completion"), lambda model: model.complete(REQUEST), "c1"
    )
    model = model_over(CassetteReplayTransport(store.load("c1"), CassetteRedactor([KEY])))
    changed = ModelRequest(
        system="Be brief.", prompt="Open chapter two.", max_output_tokens=300, prompt_version="v2"
    )
    with pytest.raises(ApplicationError) as error:
        model.complete(changed)
    assert error.value.code == "CASSETTE_MISMATCH"
    assert not isinstance(error.value, TransientStageError)
    assert "differs in: messages" in error.value.message


def test_a_recorded_failure_replays_as_the_same_kind_of_failure(tmp_path: Path) -> None:
    store = record(
        tmp_path, provider_answering("error_credit"), lambda model: model.complete(REQUEST), "dry"
    )
    with pytest.raises(CapacityExhaustedError):
        model_over(CassetteReplayTransport(store.load("dry"), CassetteRedactor([KEY]))).complete(
            REQUEST
        )


def test_a_key_the_provider_echoes_back_is_masked_in_the_cassette_but_not_for_the_caller(
    tmp_path: Path,
) -> None:
    store = JsonCassetteStore(tmp_path, CassetteRedactor([KEY]))
    transport = CassetteRecordingTransport(
        provider_answering("error_auth", echo_key=True), CassetteRedactor([KEY]), store
    )
    with pytest.raises(CapacityExhaustedError) as live:
        model_over(transport).complete(REQUEST)
    assert KEY in str(live.value)
    transport.finish("echoed", "anthropic")
    assert KEY not in (tmp_path / "echoed.json").read_text(encoding="utf-8")
    with pytest.raises(CapacityExhaustedError) as replayed:
        model_over(CassetteReplayTransport(store.load("echoed"), CassetteRedactor([KEY]))).complete(
            REQUEST
        )
    assert KEY not in str(replayed.value)
    assert "[REDACTED]" in str(replayed.value)
