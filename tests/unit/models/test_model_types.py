"""The vendor-neutral model types: validation and the integer cost arithmetic."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor


def descriptor(**changes: object) -> ProviderDescriptor:
    values: dict[str, object] = {
        "provider": "acme",
        "model": "acme-1",
        "family": "acme",
        "context_window": 200_000,
        "max_output_tokens": 8_000,
        "input_micro_usd_per_mtok": 3_000_000,
        "output_micro_usd_per_mtok": 15_000_000,
        "cache_read_micro_usd_per_mtok": 300_000,
        "cache_write_micro_usd_per_mtok": 3_750_000,
        "batch_discount_percent": 50,
        "price_effective": "2026-11-01",
        "usage_policy_url": "https://example.test/policy",
    }
    values.update(changes)
    return ProviderDescriptor(**values)  # type: ignore[arg-type]


def test_availability_has_the_four_states_a_run_must_tell_apart() -> None:
    assert [m.value for m in ModelAvailability] == [
        "available",
        "window_exhausted",
        "credits_exhausted",
        "authentication_failed",
    ]


@pytest.mark.parametrize(
    "fields",
    [
        {"input_tokens": -1, "output_tokens": 0},
        {"input_tokens": 0, "output_tokens": -1},
        {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": -1},
        {"input_tokens": 0, "output_tokens": 0, "cache_write_tokens": -1},
    ],
)
def test_usage_refuses_negative_counts(fields: dict[str, int]) -> None:
    with pytest.raises(ValueError, match="negative"):
        ModelUsage(**fields)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"prompt": "  "}, "needs a prompt"),
        ({"max_output_tokens": 0}, "positive output cap"),
        ({"prompt_version": " "}, "prompt version"),
    ],
)
def test_request_refuses_what_cannot_be_sent(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "system": "s",
        "prompt": "p",
        "max_output_tokens": 10,
        "prompt_version": "v1",
    }
    values.update(changes)
    with pytest.raises(ValueError, match=message):
        ModelRequest(**values)  # type: ignore[arg-type]


def test_response_reports_truncation_and_refusal() -> None:
    usage = ModelUsage(1, 1)
    done = ModelResponse("t", usage, "snap", "end_turn")
    cut = ModelResponse("t", usage, "snap", "max_tokens")
    no = ModelResponse("", usage, "snap", "refusal")
    assert (done.was_truncated(), done.was_refused()) == (False, False)
    assert (cut.was_truncated(), cut.was_refused()) == (True, False)
    assert (no.was_truncated(), no.was_refused()) == (False, True)


def test_response_refuses_an_unknown_stop_reason_or_a_missing_snapshot() -> None:
    usage = ModelUsage(1, 1)
    with pytest.raises(ValueError, match="stop reason"):
        ModelResponse("t", usage, "snap", "length")
    with pytest.raises(ValueError, match="snapshot"):
        ModelResponse("t", usage, " ", "end_turn")


@pytest.mark.parametrize(
    "changes",
    [
        {"provider": " "},
        {"model": ""},
        {"family": " "},
    ],
)
def test_descriptor_needs_an_identity(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="provider, a model and a family"):
        descriptor(**changes)


@pytest.mark.parametrize("changes", [{"context_window": 0}, {"max_output_tokens": 0}])
def test_descriptor_needs_positive_limits(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="positive limits"):
        descriptor(**changes)


@pytest.mark.parametrize(
    "name",
    [
        "input_micro_usd_per_mtok",
        "output_micro_usd_per_mtok",
        "cache_read_micro_usd_per_mtok",
        "cache_write_micro_usd_per_mtok",
    ],
)
def test_descriptor_refuses_a_negative_price(name: str) -> None:
    with pytest.raises(ValueError, match="negative"):
        descriptor(**{name: -1})


@pytest.mark.parametrize("percent", [-1, 101])
def test_descriptor_refuses_a_batch_discount_outside_zero_to_hundred(percent: int) -> None:
    with pytest.raises(ValueError, match="0 to 100"):
        descriptor(batch_discount_percent=percent)


def test_cost_is_exact_for_round_numbers() -> None:
    usage = ModelUsage(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        cache_read_tokens=1_000_000,
        cache_write_tokens=1_000_000,
    )
    assert descriptor().cost_micro_usd(usage) == 3_000_000 + 15_000_000 + 300_000 + 3_750_000


def test_cost_rounds_up_to_a_whole_micro_dollar() -> None:
    # 1 token at 3,000,000 micro-USD per million is exactly 3; 1 cache-read token is 0.3 -> 1.
    assert descriptor().cost_micro_usd(ModelUsage(1, 0)) == 3
    assert descriptor().cost_micro_usd(ModelUsage(0, 0, cache_read_tokens=1)) == 1
    assert descriptor().cost_micro_usd(ModelUsage(0, 0)) == 0


def test_batch_discount_applies_and_still_rounds_up() -> None:
    usage = ModelUsage(1_000_000, 0)
    assert descriptor().cost_micro_usd(usage, batch=True) == 1_500_000
    # 1 output token is 15 micro-USD; half is 7.5, which rounds up to 8.
    assert descriptor().cost_micro_usd(ModelUsage(0, 1), batch=True) == 8
    assert descriptor(batch_discount_percent=0).cost_micro_usd(usage, batch=True) == 3_000_000


def test_worst_case_prices_input_at_the_dearer_rate_and_output_at_its_cap() -> None:
    d = descriptor()
    assert d.worst_case_micro_usd(1_000_000, 1_000_000) == 3_750_000 + 15_000_000
    cheap_write = descriptor(cache_write_micro_usd_per_mtok=1)
    assert cheap_write.worst_case_micro_usd(1_000_000, 0) == 3_000_000


def test_worst_case_refuses_negative_counts() -> None:
    with pytest.raises(ValueError, match="negative"):
        descriptor().worst_case_micro_usd(-1, 0)
    with pytest.raises(ValueError, match="negative"):
        descriptor().worst_case_micro_usd(0, -1)


@given(
    fresh=st.integers(0, 500_000),
    cached=st.integers(0, 500_000),
    written=st.integers(0, 500_000),
    output=st.integers(0, 8_000),
    extra_output=st.integers(0, 100),
)
def test_a_reservation_never_falls_short_of_the_real_cost(
    fresh: int, cached: int, written: int, output: int, extra_output: int
) -> None:
    d = descriptor()
    usage = ModelUsage(fresh, output, cache_read_tokens=cached, cache_write_tokens=written)
    reserved = d.worst_case_micro_usd(fresh + cached + written, output + extra_output)
    assert d.cost_micro_usd(usage) <= reserved
    assert d.cost_micro_usd(usage, batch=True) <= d.cost_micro_usd(usage)


def test_a_valid_request_is_accepted_as_given() -> None:
    request = ModelRequest(system="s", prompt="p", max_output_tokens=10, prompt_version="v1")
    assert (request.system, request.prompt, request.max_output_tokens, request.prompt_version) == (
        "s",
        "p",
        10,
        "v1",
    )
