"""The REST guard end to end: authentication, brute-force throttling, rate limits."""

from fastapi.testclient import TestClient
from starlette.requests import Request

from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.security.constant_time_api_key_verifier import (
    ConstantTimeApiKeyVerifier,
)
from engineering_influence.infrastructure.security.token_bucket_rate_limiter import (
    TokenBucketRateLimiter,
)
from engineering_influence.interaction.api.api_guard import ApiGuard
from engineering_influence.interaction.api.application import ApiApplication
from engineering_influence.interfaces.rate_limiter_port import RateLimiterPort

KEY = "a-valid-api-key-0123456789"  # gitleaks:allow
PROJECT = {"slug": "demo", "title": "Demo", "postulates": ["Evidence first."], "stages": ["thesis"]}


def client(burst: float = 100.0) -> TestClient:
    guard = ApiGuard(
        ConstantTimeApiKeyVerifier([KEY]), TokenBucketRateLimiter(burst=burst, per_second=0.0001)
    )
    return TestClient(ApiApplication(InMemoryLedger(), InMemoryQueue(), guard).build())


def test_a_request_without_a_key_is_unauthorized() -> None:
    response = client().post("/v1/pipelines", json=PROJECT)

    assert response.status_code == 401
    assert response.json() == {
        "code": "UNAUTHORIZED",
        "message": "a valid API key is required",
        "retryable": False,
    }


def test_a_wrong_key_is_unauthorized() -> None:
    response = client().post(
        "/v1/pipelines", json=PROJECT, headers={"Authorization": "Bearer not-the-key"}
    )

    assert response.status_code == 401


def test_bearer_and_header_keys_are_both_accepted() -> None:
    api = client()

    bearer = api.post("/v1/pipelines", json=PROJECT, headers={"Authorization": f"Bearer {KEY}"})
    header = api.post("/v1/pipelines", json=PROJECT, headers={"X-API-Key": KEY})

    assert bearer.status_code == 200
    assert header.status_code == 200


def test_the_scheme_is_case_insensitive_but_other_schemes_are_not_keys() -> None:
    api = client()

    assert (
        api.post(
            "/v1/pipelines", json=PROJECT, headers={"Authorization": f"bearer {KEY}"}
        ).status_code
        == 200
    )
    assert (
        api.post(
            "/v1/pipelines", json=PROJECT, headers={"Authorization": f"Basic {KEY}"}
        ).status_code
        == 401
    )
    assert (
        api.post("/v1/pipelines", json=PROJECT, headers={"Authorization": "Bearer "}).status_code
        == 401
    )


def test_key_guessing_is_throttled_before_the_key_is_compared() -> None:
    api = client(burst=3)
    wrong = {"Authorization": "Bearer guess"}

    statuses = [
        api.post("/v1/pipelines", json=PROJECT, headers=wrong).status_code for _ in range(5)
    ]
    right = api.post("/v1/pipelines", json=PROJECT, headers={"Authorization": f"Bearer {KEY}"})

    assert statuses == [401, 401, 401, 429, 429]
    assert right.status_code == 429


def test_rate_limit_response_is_retryable() -> None:
    api = client(burst=1)
    headers = {"Authorization": f"Bearer {KEY}"}
    api.post("/v1/pipelines", json=PROJECT, headers=headers)

    limited = api.post("/v1/pipelines", json=PROJECT, headers=headers)

    assert limited.status_code == 429
    assert limited.json()["retryable"] is True
    assert limited.json()["code"] == "RATE_LIMITED"


class RecordingLimiter(RateLimiterPort):
    """Admits everything except keys with a denied prefix, and records what it was asked."""

    def __init__(self, denied_prefix: str = "") -> None:
        self.keys: list[str] = []
        self._denied_prefix = denied_prefix

    def allow(self, key: str) -> bool:
        self.keys.append(key)
        return not (self._denied_prefix and key.startswith(self._denied_prefix))


def test_a_per_key_budget_applies_after_authentication() -> None:
    limiter = RecordingLimiter(denied_prefix="key:")
    guard = ApiGuard(ConstantTimeApiKeyVerifier([KEY]), limiter)
    api = TestClient(ApiApplication(InMemoryLedger(), InMemoryQueue(), guard).build())

    response = api.post("/v1/pipelines", json=PROJECT, headers={"Authorization": f"Bearer {KEY}"})

    assert response.status_code == 429
    assert [key.split(":")[0] for key in limiter.keys] == ["ip", "key"]


def test_the_raw_api_key_never_reaches_the_limiter() -> None:
    limiter = RecordingLimiter()
    guard = ApiGuard(ConstantTimeApiKeyVerifier([KEY]), limiter)
    api = TestClient(ApiApplication(InMemoryLedger(), InMemoryQueue(), guard).build())

    api.post("/v1/pipelines", json=PROJECT, headers={"Authorization": f"Bearer {KEY}"})

    assert all(KEY not in key for key in limiter.keys)


def test_an_unauthenticated_request_is_never_charged_to_a_key() -> None:
    limiter = RecordingLimiter()
    guard = ApiGuard(ConstantTimeApiKeyVerifier([KEY]), limiter)
    api = TestClient(ApiApplication(InMemoryLedger(), InMemoryQueue(), guard).build())

    api.post("/v1/pipelines", json=PROJECT, headers={"Authorization": "Bearer wrong"})

    assert [key.split(":")[0] for key in limiter.keys] == ["ip"]


def test_a_request_with_no_client_address_is_still_guarded() -> None:
    guard = ApiGuard(ConstantTimeApiKeyVerifier([KEY]), TokenBucketRateLimiter(1, 0.0001))
    scope = {"type": "http", "headers": [(b"authorization", f"Bearer {KEY}".encode())]}

    guard(Request(scope))  # no client in scope: falls back to a shared "unknown" bucket
