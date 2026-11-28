# Webhooks

The worker tells your systems about a run as it moves. Set `EI_WEBHOOK_URLS` to receivers you control, and the
worker sends each event to each of them. With no receiver set, nothing is sent and nothing is queued.

## Events

| Event | When | Payload keys |
|---|---|---|
| `pipeline.started` | a run starts | `project_slug`, `remaining_stages`, `stage` |
| `phase.completed` | a stage finishes | `artifact_id`, `job_id`, `phase`, `project_slug` |
| `gate.awaiting` | a run waits for a spend decision | `gate`, `job_id`, `phase`, `project_slug` |
| `pipeline.completed` | every stage has finished | `project_slug` |
| `pipeline.failed` | a run stops for a reason it cannot recover from, or overspends its budget | `code`, `project_slug`, `stage` |

`project_slug` is the run's id. `job_id` is `<run>/<stage>`, and `artifact_id` is `<run>/<stage>.md`.
`code` is why the run stopped: `stage-failed` (the stage's error cannot be retried), `retries-exhausted` (a transient error after the last attempt), or `budget-exceeded` (the journal records more spend than the cap). The event carries the code and never the error text, since a stage's error can quote its input. A run that is parked for a capacity limit, or waits for a spend decision, sends no failure event; it sends `gate.awaiting` for the decision.

## Headers and body

Each delivery is a `POST` with a JSON body of the form `{"schema_version": 1, "id": ..., "type": ..., "data": {...}}`,
and these headers:

- `X-Engineering-Influence-Event`: the event name.
- `X-Engineering-Influence-Event-Id`: the event id. It is the same on every retry, so a receiver can ignore a repeat.
- `X-Engineering-Influence-Timestamp`: the Unix time the delivery was signed.
- `X-Engineering-Influence-Signature`: `v1=<hex>`, the HMAC-SHA256 of `"<timestamp>." + body`, keyed by `EI_WEBHOOK_SECRET`.

Verify the raw body, not a re-serialised copy. Check the signature, then the timestamp window, then replays, in that
order. The stack's own verifier does this (`SignedRequestVerifier`).

## Verifying a delivery

```python
import hashlib
import hmac
import time


def verify(secret: bytes, body: bytes, timestamp: str, signature: str, window: int = 300) -> bool:
    if abs(time.time() - int(timestamp)) > window:
        return False
    expected = "v1=" + hmac.new(secret, f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Your receiver must also remember recent event ids and ignore a repeat, since a delivery can arrive more than once.

## Delivery

- Each event is queued in the same commit as the run's change, so a stored change always has its event queued.
- The worker delivers queued events every `EI_WEBHOOK_INTERVAL_SECONDS` (default 5). A receiver that answers with a
  2xx status has the event marked delivered.
- Any other answer, or no answer, counts as a failed attempt. After five attempts the event is dead-lettered, and an
  error alert is raised. A failure never stops the other events from being delivered.
- Destinations must be public `https://` addresses; private or local addresses are refused.
- Delivery is at least once. The event id lets a receiver drop repeats.

## The secret

`EI_WEBHOOK_SECRET` is read from the environment at start-up and is never printed or logged. The settings never show it
in their text form. Set it in your deployment's secret store, and rotate it by changing the variable and restarting the
worker; deliveries signed under the old secret will fail verification at the receiver until it is updated.
