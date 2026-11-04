"""Shared loader for the sample project fixture used by every example."""

import json
from pathlib import Path
from typing import Any

from engineering_influence.infrastructure.security.constant_time_api_key_verifier import (
    ConstantTimeApiKeyVerifier,
)
from engineering_influence.infrastructure.security.token_bucket_rate_limiter import (
    TokenBucketRateLimiter,
)
from engineering_influence.interaction.api.api_guard import ApiGuard


class SampleProject:
    """Reads the bundled sample project."""

    PATH = Path(__file__).parent / "sample_project" / "project.json"

    def load(self) -> dict[str, Any]:
        """Return the sample project as a plain dictionary."""
        data: dict[str, Any] = json.loads(self.PATH.read_text(encoding="utf-8"))
        return data


class SampleGuard:
    """An API guard for the examples. Real deployments read keys from EI_API_KEYS."""

    # A placeholder for the examples only; never reuse it outside them.
    API_KEY = "example-key-for-local-demos-only"  # gitleaks:allow

    def build(self) -> ApiGuard:
        """Return a guard that accepts the example key."""
        return ApiGuard(
            ConstantTimeApiKeyVerifier([self.API_KEY]),
            TokenBucketRateLimiter(burst=20, per_second=20),
        )
