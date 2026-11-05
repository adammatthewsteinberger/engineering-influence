# /// script
# requires-python = ">=3.12"
# dependencies = ["requests>=2.32,<3"]
# ///
"""Deliver a signed event to a receiver and show how tampering and replay are refused.

    # terminal 1
    export EI_WEBHOOK_SECRET=$(openssl rand -hex 24)
    python3 examples/webhooks/receiver.py
    # terminal 2 (same secret)
    uv run examples/webhooks/send_event.py

This reproduces the request the platform's outbound delivery makes (same body, same
headers), so you can develop and test a receiver without waiting for a real event. The
stack's worker does not emit webhooks yet; see docs/CONFIGURATION.md, "Limits to know".
"""

import hashlib
import hmac
import json
import os
import sys
import time

import requests

URL = os.environ.get("EI_RECEIVER_URL", "http://127.0.0.1:9000/")


def delivery(secret: bytes, event_id: str, sent_at: int) -> tuple[bytes, dict[str, str]]:
    """Build the body and headers exactly as WebhookDelivery does."""
    body = json.dumps(
        {"id": event_id, "type": "phase.completed", "data": {"slug": "sample-essay"}},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    digest = hmac.new(secret, f"{sent_at}.".encode() + body, hashlib.sha256).hexdigest()
    return body, {
        "Content-Type": "application/json",
        "X-Engineering-Influence-Signature": f"v1={digest}",
        "X-Engineering-Influence-Timestamp": str(sent_at),
        "X-Engineering-Influence-Event": "phase.completed",
        "X-Engineering-Influence-Event-Id": event_id,
    }


def post(label: str, body: bytes, headers: dict[str, str]) -> None:
    answer = requests.post(URL, data=body, headers=headers, timeout=5)
    print(f"{label}: {answer.status_code} {answer.json()['status']}")


def main() -> int:
    raw = os.environ.get("EI_WEBHOOK_SECRET")
    if not raw:
        print("set EI_WEBHOOK_SECRET to the receiver's secret", file=sys.stderr)
        return 2
    secret = raw.encode()
    now = int(time.time())

    body, headers = delivery(secret, f"evt-{now}", now)
    post("first delivery", body, headers)
    post("replay of the same delivery", body, headers)
    post("tampered body", body + b" ", headers)

    old_body, old_headers = delivery(secret, f"evt-{now}-old", now - 3600)
    post("an hour old", old_body, old_headers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
