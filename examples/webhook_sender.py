"""Webhook sender/replay example: sign an event and replay it idempotently by event ID."""

import json

from engineering_influence.interaction.webhooks.signer import WebhookSigner


def main() -> None:
    signer = WebhookSigner(b"example-secret")
    seen: set[str] = set()
    event = {"event": "phase.completed", "id": "evt-1"}
    body = json.dumps(event, sort_keys=True).encode()
    for attempt in ("first delivery", "replay"):
        signature = signer.sign(body)
        fresh = event["id"] not in seen and signer.verify(body, signature)
        seen.add(event["id"])
        print(f"{attempt}: {'processed' if fresh else 'duplicate ignored'}")


if __name__ == "__main__":
    main()
