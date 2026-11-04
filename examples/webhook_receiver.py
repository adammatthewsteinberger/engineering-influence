"""Webhook receiver example: verify an HMAC-signed event, reject a tampered one."""

import json

from engineering_influence.interaction.webhooks.signer import WebhookSigner


def main() -> None:
    signer = WebhookSigner(b"example-secret")
    body = json.dumps({"event": "phase.completed", "id": "evt-1"}, sort_keys=True).encode()
    signature = signer.sign(body)
    print("valid:", signer.verify(body, signature))
    print("tampered:", signer.verify(body + b" ", signature))


if __name__ == "__main__":
    main()
