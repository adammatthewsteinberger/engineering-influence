"""Webhook receiver example: verify signature and freshness, reject tampering and replay."""

import json

from engineering_influence.interaction.webhooks.signed_request_verifier import (
    SignedRequestVerifier,
)
from engineering_influence.interaction.webhooks.signer import WebhookSigner

NOW = 1_700_000_000


def main() -> None:
    signer = WebhookSigner(b"example-secret")
    verifier = SignedRequestVerifier(signer, tolerance_seconds=300, clock=lambda: float(NOW))
    body = json.dumps({"event": "phase.completed", "id": "evt-1"}, sort_keys=True).encode()
    signature = signer.sign_at(body, NOW)
    print("valid:", verifier.verify(body, signature, str(NOW)).accepted)
    print("tampered:", verifier.verify(body + b" ", signature, str(NOW)).accepted)
    stale = signer.sign_at(body, NOW - 3600)
    print("stale:", verifier.verify(body, stale, str(NOW - 3600)).accepted)


if __name__ == "__main__":
    main()
