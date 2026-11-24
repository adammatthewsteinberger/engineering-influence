"""The webhook contract: the envelope, the catalogue of events, the headers and the signature, tied to what the services really record."""

import asyncio
import json

import httpx
from snapshot import Snapshot

from engineering_influence.contracts.job_message import JobMessage
from engineering_influence.contracts.webhook.v1.webhook_event_v1 import WebhookEventV1
from engineering_influence.infrastructure.deterministic_runner import DeterministicRunner
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.non_empty_artifact_gate import NonEmptyArtifactGate
from engineering_influence.infrastructure.security.public_https_url_policy import (
    PublicHttpsUrlPolicy,
)
from engineering_influence.infrastructure.webhooks.delivery import WebhookDelivery
from engineering_influence.infrastructure.webhooks.signer import WebhookSigner
from engineering_influence.models.pipeline_stage import PipelineStage
from engineering_influence.models.project import Project
from engineering_influence.services.process_job import ProcessJob
from engineering_influence.services.run_phase import RunPhase
from engineering_influence.services.start_pipeline import StartPipeline

SECRET = b"a-shared-secret"
NOW = 1_700_000_000


def delivered(event: str = "pipeline.started") -> tuple[bytes, httpx.Headers]:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"], seen["headers"] = request.content, request.headers
        return httpx.Response(202, request=request)

    async def send() -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        policy = PublicHttpsUrlPolicy(lambda _: ["93.184.216.34"])
        await WebhookDelivery(client, policy, lambda: float(NOW)).deliver(
            "https://receiver.test/events", event, "evt-1", {"project_slug": "demo"}, SECRET
        )
        await client.aclose()

    asyncio.run(send())
    return seen["body"], seen["headers"]  # type: ignore[return-value]


def test_the_webhook_contract_is_frozen() -> None:
    Snapshot("webhook_v1").check(
        {
            "envelope": Snapshot.schema(WebhookEventV1.model_json_schema()),
            "types": {name: list(keys) for name, keys in sorted(WebhookEventV1.TYPES.items())},
            "headers": list(WebhookEventV1.HEADERS),
            "signature": "v1=<hex HMAC-SHA256 of '<X-Engineering-Influence-Timestamp>.<body>'>",
            "body": "canonical JSON: sorted keys, no spaces",
        }
    )


def test_a_delivery_is_an_envelope_in_canonical_json_with_exactly_the_catalogued_headers() -> None:
    body, headers = delivered()
    event = WebhookEventV1.model_validate_json(body)
    assert (event.schema_version, event.id, event.type, event.data) == (
        1,
        "evt-1",
        "pipeline.started",
        {"project_slug": "demo"},
    )
    assert body == json.dumps(json.loads(body), separators=(",", ":"), sort_keys=True).encode()
    sent = {name.lower() for name in headers} - {
        "host",
        "content-length",
        "accept",
        "accept-encoding",
        "connection",
        "user-agent",
    }
    assert sent == {name.lower() for name in WebhookEventV1.HEADERS}


def test_the_signature_is_the_documented_hmac_over_the_timestamp_and_the_body() -> None:
    body, headers = delivered()
    timestamp = headers["X-Engineering-Influence-Timestamp"]
    assert timestamp == str(NOW)
    assert WebhookSigner(SECRET).verify_at(body, headers["X-Engineering-Influence-Signature"], NOW)
    assert headers["X-Engineering-Influence-Signature"].startswith("v1=")


def recorded() -> list[tuple[str, dict[str, object]]]:
    """Every event the services record, by running them: a pipeline started, a stage done, a gate waiting, a pipeline finished."""
    ledger, queue = InMemoryLedger(), InMemoryQueue()
    StartPipeline(ledger, queue).start(
        Project("demo", "Demo", ("Claim.",), (PipelineStage.THESIS, PipelineStage.BOOK))
    )
    job = ProcessJob(RunPhase(DeterministicRunner(), NonEmptyArtifactGate()), ledger, queue)
    asyncio.run(
        job.process(
            JobMessage(
                job_id="j1",
                kind="pipeline.thesis",
                payload={"project_slug": "demo", "remaining_stages": []},
            )
        )
    )
    asyncio.run(
        job.process(
            JobMessage(
                job_id="j2",
                kind="pipeline.thesis",
                payload={
                    "project_slug": "demo",
                    "gate_kind": "human",
                    "gate_name": "editor-review",
                },
            )
        )
    )
    return ledger.events


def test_the_catalogue_is_exactly_the_events_the_services_record_with_exactly_their_keys() -> None:
    events = recorded()
    assert {name for name, _ in events} == set(WebhookEventV1.TYPES)
    for name, payload in events:
        assert tuple(sorted(payload)) == WebhookEventV1.TYPES[name], name
