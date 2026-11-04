# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Per-caller token-bucket rate limiting with bounded memory."""

from collections import OrderedDict

from vibey_bootstrap.ratelimit import TokenBucket

from engineering_influence.interfaces.rate_limiter_port import RateLimiterPort


class TokenBucketRateLimiter(RateLimiterPort):
    """One bucket per caller key; the least recently seen keys are forgotten first."""

    def __init__(self, burst: float, per_second: float, max_keys: int = 10_000) -> None:
        if burst <= 0 or per_second <= 0:
            raise ValueError("burst and per_second must be positive")
        if max_keys < 1:
            raise ValueError("max_keys must be at least 1")
        self._burst = burst
        self._per_second = per_second
        self._max_keys = max_keys
        self._buckets: OrderedDict[str, TokenBucket] = OrderedDict()

    def allow(self, key: str) -> bool:
        """Consume one token for the key."""
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = TokenBucket(budget=self._burst, refill_per_second=self._per_second, name="api")
            self._buckets[key] = bucket
            if len(self._buckets) > self._max_keys:
                self._buckets.popitem(last=False)
        else:
            self._buckets.move_to_end(key)
        return bucket.consume(1.0)
