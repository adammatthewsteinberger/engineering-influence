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
        """Return the versioned signature header value."""
        digest = hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
        return f"v1={digest}"

    def verify(self, payload: bytes, signature: str) -> bool:
        """Constant-time verify a versioned signature header."""
        expected = self.sign(payload)
        return hmac.compare_digest(expected, signature)
