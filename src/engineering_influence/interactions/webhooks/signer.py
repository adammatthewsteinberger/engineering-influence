# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""HMAC signing and verification for webhook payloads."""

import hashlib
import hmac


class WebhookSigner:
    """Signs canonical UTF-8 payloads with an HMAC-SHA256 secret."""

    def __init__(self, secret: bytes) -> None:
        if not secret:
            raise ValueError("webhook secret is required")
        self._secret = secret

    def sign(self, payload: bytes) -> str:
        """Return the versioned signature header value for the bare payload."""
        digest = hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
        return f"v1={digest}"

    def verify(self, payload: bytes, signature: str) -> bool:
        """Constant-time verify a versioned signature header."""
        expected = self.sign(payload)
        return hmac.compare_digest(expected, signature)

    def sign_at(self, payload: bytes, timestamp: int) -> str:
        """Sign ``<timestamp>.<payload>`` so a captured delivery cannot be replayed later."""
        return self.sign(f"{timestamp}.".encode() + payload)

    def verify_at(self, payload: bytes, signature: str, timestamp: int) -> bool:
        """Constant-time verify a timestamp-bound signature."""
        return self.verify(f"{timestamp}.".encode() + payload, signature)
