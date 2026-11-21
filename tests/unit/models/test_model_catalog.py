"""The catalog picks the price in force on a date and refuses to guess; long-context pricing."""

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.model_catalog import ModelCatalog
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor


def priced(effective: str, rate: int = 1_000_000, **changes: object) -> ProviderDescriptor:
    values: dict[str, object] = {
        "provider": "acme",
        "model": "acme-1",
        "family": "acme",
        "context_window": 200_000,
        "max_output_tokens": 8_000,
        "input_micro_usd_per_mtok": rate,
        "output_micro_usd_per_mtok": rate * 5,
        "cache_read_micro_usd_per_mtok": rate // 10,
        "cache_write_micro_usd_per_mtok": rate + rate // 4,
        "batch_discount_percent": 50,
        "price_effective": effective,
        "usage_policy_url": "https://example.test/policy",
    }
    values.update(changes)
    return ProviderDescriptor(**values)  # type: ignore[arg-type]


JAN, JUL = priced("2026-01-01", 3_000_000), priced("2026-07-01", 2_000_000)
CATALOG = ModelCatalog((JUL, JAN, priced("2026-01-01", 9, model="other")))


def test_the_latest_price_effective_by_the_date_is_used() -> None:
    assert CATALOG.descriptor("acme", "acme-1", date(2026, 3, 1)) is JAN
    assert CATALOG.descriptor("acme", "acme-1", date(2026, 7, 1)) is JUL
    assert CATALOG.descriptor("acme", "acme-1", date(2030, 1, 1)) is JUL


def test_a_price_applies_from_its_effective_day_not_the_day_before() -> None:
    assert CATALOG.descriptor("acme", "acme-1", date(2026, 1, 1)) is JAN
    assert CATALOG.descriptor("acme", "acme-1", date(2026, 6, 30)) is JAN
    with pytest.raises(ApplicationError):
        CATALOG.descriptor("acme", "acme-1", date(2025, 12, 31))


@pytest.mark.parametrize(
    ("provider", "model"), [("acme", "missing"), ("nobody", "acme-1"), ("acme", "other-2")]
)
def test_an_unpriced_model_is_refused_with_a_message_that_says_how_to_fix_it(
    provider: str, model: str
) -> None:
    with pytest.raises(ApplicationError) as caught:
        CATALOG.descriptor(provider, model, date(2026, 8, 1))
    assert caught.value.code == "MODEL_UNPRICED"
    assert f"{provider}/{model}" in caught.value.message
    assert "2026-08-01" in caught.value.message
    assert caught.value.http_status == 503


def test_a_model_is_matched_by_provider_as_well_as_name() -> None:
    other = priced("2026-01-01", 5, provider="elsewhere")
    catalog = ModelCatalog((JAN, other))
    assert catalog.descriptor("elsewhere", "acme-1", date(2026, 2, 1)) is other


def test_two_prices_with_one_effective_date_are_refused() -> None:
    with pytest.raises(ValueError, match="same effective date"):
        ModelCatalog((JAN, priced("2026-01-01", 1)))


def test_an_empty_catalog_prices_nothing() -> None:
    with pytest.raises(ApplicationError):
        ModelCatalog(()).descriptor("acme", "acme-1", date(2026, 1, 1))


@pytest.mark.parametrize("effective", ["next tuesday", "2026-13-01", ""])
def test_a_descriptor_needs_a_real_effective_date(effective: str) -> None:
    with pytest.raises(ValueError, match="ISO date"):
        priced(effective)


LONG = priced(
    "2026-01-01",
    1_000_000,
    long_context_threshold_tokens=1000,
    long_context_input_percent=200,
    long_context_output_percent=150,
)


def test_a_prompt_at_the_threshold_is_standard_and_one_token_over_is_long() -> None:
    at = LONG.cost_micro_usd(ModelUsage(1000, 0))
    over = LONG.cost_micro_usd(ModelUsage(1001, 0))
    assert at == 1000
    assert over == 2002


def test_the_threshold_counts_cached_tokens_as_prompt() -> None:
    usage = ModelUsage(input_tokens=100, output_tokens=0, cache_read_tokens=901)
    # 1,001 prompt tokens: long. 100 x 1.00 + 901 x 0.10 = 190.1, doubled = 380.2, rounded up.
    assert LONG.cost_micro_usd(usage) == 381


def test_the_long_tier_scales_input_and_output_by_their_own_percentages() -> None:
    usage = ModelUsage(input_tokens=2000, output_tokens=100)
    # input 2000 x 1.00 x 2.0 = 4000; output 100 x 5.00 x 1.5 = 750.
    assert LONG.cost_micro_usd(usage) == 4750
    assert LONG.cost_micro_usd(usage, batch=True) == 2375


def test_the_worst_case_applies_the_long_tier_only_when_the_prompt_can_reach_it() -> None:
    # 1,000 input tokens at the dearer cache-write rate 1.25 = 1,250; output 100 x 5.00 = 500.
    assert LONG.worst_case_micro_usd(1000, 100) == 1250 + 500
    # 1,001 input tokens at the dearer cache-write rate 1.25, doubled; output 100 x 5.00 x 1.5.
    assert LONG.worst_case_micro_usd(1001, 100) == 2503 + 750


@pytest.mark.parametrize(
    "changes",
    [
        {"long_context_threshold_tokens": -1},
        {"long_context_input_percent": 99},
        {"long_context_output_percent": 99},
    ],
)
def test_a_long_context_tier_cannot_be_negative_or_cheaper(changes: dict[str, int]) -> None:
    with pytest.raises(ValueError, match="long-context"):
        priced("2026-01-01", **changes)


@pytest.mark.parametrize(
    "changes",
    [{"long_context_input_percent": 200}, {"long_context_output_percent": 150}],
)
def test_long_context_percentages_without_a_threshold_are_refused(changes: dict[str, int]) -> None:
    with pytest.raises(ValueError, match="need a long-context threshold"):
        priced("2026-01-01", **changes)


@given(
    fresh=st.integers(0, 400_000),
    cached=st.integers(0, 400_000),
    written=st.integers(0, 400_000),
    output=st.integers(0, 8_000),
    extra=st.integers(0, 100),
)
def test_a_long_context_reservation_still_covers_the_real_cost(
    fresh: int, cached: int, written: int, output: int, extra: int
) -> None:
    d = priced(
        "2026-01-01",
        3_000_000,
        long_context_threshold_tokens=200_000,
        long_context_input_percent=200,
        long_context_output_percent=150,
    )
    usage = ModelUsage(fresh, output, cache_read_tokens=cached, cache_write_tokens=written)
    reserved = d.worst_case_micro_usd(fresh + cached + written, output + extra)
    assert d.cost_micro_usd(usage) <= reserved
    assert d.cost_micro_usd(usage, batch=True) <= d.cost_micro_usd(usage)
