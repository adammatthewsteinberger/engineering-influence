"""Webhook sender/replay example: a captured delivery is accepted once and then refused."""

import json

from engineering_influence.interaction.webhooks.signed_request_verifier import (
    SignedRequestVerifier,
)
from engineering_influence.interaction.webhooks.signer import WebhookSigner

NOW = 1_700_000_000


def main() -> None:
    signer = WebhookSigner(b"example-secret")
    verifier = SignedRequestVerifier(signer, clock=lambda: float(NOW))
    body = json.dumps({"event": "phase.completed", "id": "evt-1"}, sort_keys=True).encode()
    signature = signer.sign_at(body, NOW)
    for attempt in ("first delivery", "replay"):
        fresh = verifier.verify(body, signature, str(NOW)).accepted
        print(f"{attempt}: {'processed' if fresh else 'duplicate ignored'}")


if __name__ == "__main__":
    main()
