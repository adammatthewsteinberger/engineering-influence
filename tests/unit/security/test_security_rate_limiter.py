"""Token-bucket rate limiting."""

import pytest

from engineering_influence.infrastructure.security.token_bucket_rate_limiter import (
    TokenBucketRateLimiter,
)

SLOW = 0.0001


def test_burst_is_admitted_then_refused() -> None:
    limiter = TokenBucketRateLimiter(burst=3, per_second=SLOW)

    assert [limiter.allow("a") for _ in range(5)] == [True, True, True, False, False]


def test_callers_do_not_share_a_budget() -> None:
    limiter = TokenBucketRateLimiter(burst=1, per_second=SLOW)

    assert limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")


def test_memory_is_bounded_and_oldest_callers_are_forgotten() -> None:
    limiter = TokenBucketRateLimiter(burst=1, per_second=SLOW, max_keys=2)
    limiter.allow("a")
    limiter.allow("b")
    limiter.allow("c")

    assert limiter.allow("a")  # evicted, so it starts again with a fresh bucket
    assert not limiter.allow("c")  # still tracked and already spent


def test_recently_used_caller_survives_eviction() -> None:
    limiter = TokenBucketRateLimiter(burst=1, per_second=SLOW, max_keys=2)
    limiter.allow("a")
    limiter.allow("b")
    limiter.allow("a")  # refresh a
    limiter.allow("c")  # evicts b, not a

    assert not limiter.allow("a")


@pytest.mark.parametrize(("burst", "per_second", "max_keys"), [(0, 1, 1), (1, 0, 1), (1, 1, 0)])
def test_invalid_limits_are_rejected(burst: float, per_second: float, max_keys: int) -> None:
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(burst=burst, per_second=per_second, max_keys=max_keys)
