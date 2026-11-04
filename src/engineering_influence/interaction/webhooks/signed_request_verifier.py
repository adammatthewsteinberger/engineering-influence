# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Inbound webhook authentication: signature, freshness and replay."""

import time
from collections.abc import Callable

from vibey_bootstrap.auth.webhook import WebhookDedup

from engineering_influence.contracts.security_verdict import SecurityVerdict
from engineering_influence.interaction.webhooks.signer import WebhookSigner
from engineering_influence.interfaces.webhook_verifier_port import WebhookVerifierPort


class SignedRequestVerifier(WebhookVerifierPort):
    """Accept a delivery once: correctly signed, recent, and not seen before."""

    def __init__(
        self,
        signer: WebhookSigner,
        tolerance_seconds: int = 300,
        clock: Callable[[], float] = time.time,
        dedup: WebhookDedup | None = None,
    ) -> None:
        if tolerance_seconds < 1:
            raise ValueError("tolerance_seconds must be at least 1")
        self._signer = signer
        self._tolerance = tolerance_seconds
        self._clock = clock
        self._dedup = dedup or WebhookDedup(ttl_seconds=float(tolerance_seconds * 2))

    def verify(self, body: bytes, signature: str | None, timestamp: str | None) -> SecurityVerdict:
        """Check order matters: authenticate before recording anything for replay."""
        if not signature or not timestamp:
            return SecurityVerdict.reject("missing_signature")
        try:
            sent_at = int(timestamp)
        except ValueError:
            return SecurityVerdict.reject("bad_timestamp")
        if abs(self._clock() - sent_at) > self._tolerance:
            return SecurityVerdict.reject("stale_timestamp")
        if not self._signer.verify_at(body, signature, sent_at):
            return SecurityVerdict.reject("bad_signature")
        if self._dedup.already_seen((signature,)):
            return SecurityVerdict.reject("replayed")
        return SecurityVerdict.accept()
