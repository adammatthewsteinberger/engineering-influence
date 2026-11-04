# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Authentication and rate limiting for the REST interaction."""

import hashlib

from fastapi import Request

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.api_key_verifier_port import ApiKeyVerifierPort
from engineering_influence.interfaces.rate_limiter_port import RateLimiterPort


class ApiGuard:
    """FastAPI dependency: throttle by address, authenticate, then throttle by key.

    The address limit runs first so key guessing is slowed before any comparison.
    """

    def __init__(self, verifier: ApiKeyVerifierPort, limiter: RateLimiterPort) -> None:
        self._verifier = verifier
        self._limiter = limiter

    def __call__(self, request: Request) -> None:
        """Raise an ApplicationError unless the request may proceed."""
        host = request.client.host if request.client else "unknown"
        self._admit(f"ip:{host}")
        presented = self._presented_key(request)
        if presented is None or not self._verifier.verify(presented):
            raise ApplicationError(
                code="UNAUTHORIZED", message="a valid API key is required", http_status=401
            )
        self._admit(f"key:{hashlib.sha256(presented.encode()).hexdigest()[:16]}")

    def _admit(self, key: str) -> None:
        if not self._limiter.allow(key):
            raise ApplicationError(
                code="RATE_LIMITED",
                message="too many requests",
                retryable=True,
                http_status=429,
            )

    @staticmethod
    def _presented_key(request: Request) -> str | None:
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token.strip():
            return token.strip()
        return request.headers.get("x-api-key")
