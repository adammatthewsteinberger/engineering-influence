"""A webhook receiver, using only the standard library.

    export EI_WEBHOOK_SECRET=$(openssl rand -hex 24)
    python3 examples/webhooks/receiver.py            # listens on 127.0.0.1:9000

Verification is what the delivery format asks of any consumer, in this order:

1. the signature: `X-Engineering-Influence-Signature: v1=<hex>`, where the hex is
   HMAC-SHA256(secret, "<timestamp>." + raw body bytes);
2. the timestamp (`X-Engineering-Influence-Timestamp`, Unix seconds) is within five minutes;
3. the signature has not been seen before (replay).

Answers: 202 accepted, 401 rejected (bad or missing signature, stale timestamp), 409 replay.
`SignedRequestVerifier` in this package implements the same checks for Python services.
"""

import hashlib
import hmac
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOLERANCE_SECONDS = 300
SEEN: dict[str, float] = {}  # signature -> expiry; use a shared store when you run replicas


def verify(secret: bytes, body: bytes, signature: str, timestamp: str) -> str:
    """Return "ok" or the reason the delivery must be refused."""
    try:
        sent_at = int(timestamp)
    except ValueError:
        return "bad_timestamp"
    if abs(time.time() - sent_at) > TOLERANCE_SECONDS:
        return "stale_timestamp"
    expected = "v1=" + hmac.new(secret, f"{sent_at}.".encode() + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return "bad_signature"
    now = time.time()
    for old in [key for key, expiry in SEEN.items() if expiry < now]:
        del SEEN[old]
    if signature in SEEN:
        return "replayed"
    SEEN[signature] = now + 2 * TOLERANCE_SECONDS
    return "ok"


class Receiver(BaseHTTPRequestHandler):
    secret = b""

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        reason = verify(
            self.secret,
            body,
            self.headers.get("X-Engineering-Influence-Signature", ""),
            self.headers.get("X-Engineering-Influence-Timestamp", ""),
        )
        if reason == "ok":
            event = json.loads(body)
            print(f"accepted {event['type']} {event['id']}", flush=True)
            self._reply(202, {"status": "accepted"})
        else:
            print(f"refused: {reason}", flush=True)
            self._reply(409 if reason == "replayed" else 401, {"status": reason})

    def _reply(self, status: int, payload: dict[str, str]) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:
        pass  # we print our own, shorter line


def main() -> int:
    secret = os.environ.get("EI_WEBHOOK_SECRET")
    if not secret:
        print("set EI_WEBHOOK_SECRET (the receiver refuses to run unsigned)", file=sys.stderr)
        return 2
    Receiver.secret = secret.encode()
    port = int(os.environ.get("EI_RECEIVER_PORT", "9000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Receiver)
    print(f"listening on http://127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
