"""Shared fixtures."""

import pytest

from engineering_influence.infrastructure.security.constant_time_api_key_verifier import (
    ConstantTimeApiKeyVerifier,
)
from engineering_influence.infrastructure.security.token_bucket_rate_limiter import (
    TokenBucketRateLimiter,
)
from engineering_influence.interaction.api.api_guard import ApiGuard

TEST_API_KEY = "test-api-key-0123456789abcdef"  # gitleaks:allow


@pytest.fixture
def api_key() -> str:
    """A key the shared guard accepts."""
    return TEST_API_KEY


@pytest.fixture
def api_guard() -> ApiGuard:
    """A guard with generous limits and one valid key."""
    return ApiGuard(
        ConstantTimeApiKeyVerifier([TEST_API_KEY]),
        TokenBucketRateLimiter(burst=100, per_second=100),
    )
