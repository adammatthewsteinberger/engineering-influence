"""Timestamped signing, inbound verification, replay defence and delivery refusal."""

import asyncio
import json
import time

import httpx
import pytest

from engineering_influence.contracts.security_verdict import SecurityVerdict
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.security.public_https_url_policy import (
    PublicHttpsUrlPolicy,
)
from engineering_influence.interaction.webhooks import (
    SignedRequestVerifier,
    WebhookDelivery,
    WebhookSigner,
)

NOW = 1_700_000_000
BODY = b'{"id":"evt-1"}'


def build(
    tolerance: int = 300, now: float = float(NOW)
) -> tuple[WebhookSigner, SignedRequestVerifier]:
    signer = WebhookSigner(b"secret")
    return signer, SignedRequestVerifier(signer, tolerance, lambda: now)


def test_timestamp_is_part_of_the_signature() -> None:
    signer = WebhookSigner(b"secret")
    signature = signer.sign_at(BODY, NOW)

    assert signer.verify_at(BODY, signature, NOW)
    assert not signer.verify_at(BODY, signature, NOW + 1)
    assert not signer.verify(BODY, signature)
    assert signature != signer.sign(BODY)


def test_a_fresh_signed_delivery_is_accepted() -> None:
    signer, verifier = build()

    assert verifier.verify(BODY, signer.sign_at(BODY, NOW), str(NOW)).accepted


def test_a_tampered_body_is_refused() -> None:
    signer, verifier = build()

    verdict = verifier.verify(BODY + b" ", signer.sign_at(BODY, NOW), str(NOW))

    assert verdict.reason == "bad_signature"


def test_a_wrong_secret_is_refused() -> None:
    _, verifier = build()
    forged = WebhookSigner(b"other").sign_at(BODY, NOW)

    assert verifier.verify(BODY, forged, str(NOW)).reason == "bad_signature"


@pytest.mark.parametrize("offset", [-301, 301, -86_400])
def test_old_and_future_deliveries_are_refused(offset: int) -> None:
    signer, verifier = build()
    sent = NOW + offset

    assert verifier.verify(BODY, signer.sign_at(BODY, sent), str(sent)).reason == (
        "stale_timestamp"
    )


def test_the_edge_of_the_window_is_still_accepted() -> None:
    signer, verifier = build()

    assert verifier.verify(BODY, signer.sign_at(BODY, NOW - 300), str(NOW - 300)).accepted


def test_a_captured_delivery_cannot_be_replayed() -> None:
    signer, verifier = build()
    signature = signer.sign_at(BODY, NOW)

    assert verifier.verify(BODY, signature, str(NOW)).accepted
    assert verifier.verify(BODY, signature, str(NOW)).reason == "replayed"


def test_forged_requests_cannot_poison_the_replay_cache() -> None:
    signer, verifier = build()
    signature = signer.sign_at(BODY, NOW)

    assert verifier.verify(BODY + b"x", signature, str(NOW)).reason == "bad_signature"
    assert verifier.verify(BODY, signature, str(NOW)).accepted


@pytest.mark.parametrize(
    ("signature", "timestamp"), [(None, "1"), ("v1=x", None), ("", ""), (None, None)]
)
def test_missing_headers_are_refused(signature: str | None, timestamp: str | None) -> None:
    _, verifier = build()

    assert verifier.verify(BODY, signature, timestamp).reason == "missing_signature"


@pytest.mark.parametrize("timestamp", ["soon", "1.5", "0x10"])
def test_a_malformed_timestamp_is_refused(timestamp: str) -> None:
    signer, verifier = build()

    assert verifier.verify(BODY, signer.sign_at(BODY, NOW), timestamp).reason == "bad_timestamp"


def test_tolerance_must_be_positive() -> None:
    with pytest.raises(ValueError, match="tolerance"):
        SignedRequestVerifier(WebhookSigner(b"secret"), tolerance_seconds=0)


def test_the_default_clock_is_wall_time() -> None:
    signer = WebhookSigner(b"secret")
    verifier = SignedRequestVerifier(signer)
    sent = int(time.time())

    assert verifier.verify(BODY, signer.sign_at(BODY, sent), str(sent)).accepted


def test_delivery_to_a_private_address_is_refused_before_any_request() -> None:
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, request=request)

    async def run() -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        policy = PublicHttpsUrlPolicy(lambda _: ["169.254.169.254"])
        try:
            await WebhookDelivery(client, policy).deliver(
                "https://metadata.example.com/", "pipeline.started", "evt-1", {}, b"secret"
            )
        finally:
            await client.aclose()

    with pytest.raises(ApplicationError) as caught:
        asyncio.run(run())
    assert caught.value.code == "WEBHOOK_TARGET_REJECTED"
    assert "non_public_address" in caught.value.message
    assert sent == []


def test_delivery_and_verifier_agree_end_to_end() -> None:
    captured: dict[str, bytes | str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content
        captured["signature"] = request.headers["X-Engineering-Influence-Signature"]
        captured["timestamp"] = request.headers["X-Engineering-Influence-Timestamp"]
        return httpx.Response(200, request=request)

    async def run() -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        policy = PublicHttpsUrlPolicy(lambda _: ["93.184.216.34"])
        try:
            await WebhookDelivery(client, policy, lambda: float(NOW)).deliver(
                "https://receiver.example.com/", "phase.completed", "evt-9", {"a": 1}, b"secret"
            )
        finally:
            await client.aclose()

    asyncio.run(run())
    _, verifier = build()
    verdict: SecurityVerdict = verifier.verify(
        bytes(captured["body"]), str(captured["signature"]), str(captured["timestamp"])
    )

    assert verdict.accepted
    assert json.loads(bytes(captured["body"]))["id"] == "evt-9"
