# Configuration

Book configuration is intentionally separate from author profile configuration.
The public package accepts a project title, slug, governing postulates, target
formats, and autonomy policy. Private books repositories may add a profile that
fills the governing-postulates slot without changing the public domain model.

The versioned configuration schema will be published under
`contracts/book_config/v1` before the first stable release.

## Security settings

Every security control fails closed: a missing or weak setting stops the service
instead of opening it.

| Setting | Meaning |
|---|---|
| `EI_API_KEYS` | Comma-separated API keys, each at least 24 characters. Required: the REST API cannot be built without a guard, and the guard cannot be built without a key. |
| Rate limits | `TokenBucketRateLimiter(burst, per_second)`. A client address is limited before its key is compared, then each key has its own budget. |
| Webhook secret | Passed to `WebhookDelivery.deliver` and `WebhookSigner`; read it with `EnvSecretProvider().require(name)` so an absent secret raises `SECRET_MISSING` (HTTP 503). |
| Webhook tolerance | `SignedRequestVerifier(tolerance_seconds=300)`: deliveries older or newer than this are refused. |

Clients send the key as `Authorization: Bearer <key>` (what the SDK does) or
`X-API-Key: <key>`.

## Webhook signature (v1)

`X-Engineering-Influence-Signature: v1=<hex>` is `HMAC-SHA256(secret, "<timestamp>." + body)`,
and `X-Engineering-Influence-Timestamp` carries the Unix time. Verify the raw
bytes, not re-serialised JSON. A receiver must check the signature, the
timestamp window and replays, in that order: `SignedRequestVerifier` does.

## Outbound destinations

`WebhookDelivery` requires an `OutboundUrlPolicyPort`. `PublicHttpsUrlPolicy`
allows only `https` URLs without embedded credentials whose every resolved
address is publicly routable, which blocks loopback, private ranges and cloud
metadata addresses. It resolves the name when called, so DNS rebinding is still
possible; route deliveries to untrusted URLs through an egress proxy as well.

## Not covered yet

- No upload or inbound-webhook HTTP route exists, so `AttachmentUploadInspector`
  and `SignedRequestVerifier` are building blocks that no endpoint uses yet.
- The MCP server (stdio) and the CLI are local processes and are not
  authenticated; do not expose them on a network.
- Request body size limits, TLS termination, and API key rotation are
  deployment concerns for the reverse proxy and are not implemented here.
- `pdf_safety` is a best-effort scrubber for pass-through PDFs and is not wired
  in because the service never passes uploaded PDFs on.

## Observability

Wire these adapters in the process entry point. Nothing is global except what
`vibey_bootstrap` itself keeps (counters, latency statistics, alert state).

| Concern | Use |
|---|---|
| JSON logs | `JsonLoggingConfigurator(level).configure()`: one JSON line per record on stderr, secrets masked, `correlation_id` on every line. Safe to call twice. |
| Correlation | `ContextVarCorrelation` plus `CorrelatingQueue(queue, correlation)` on the API side and `CorrelatedPhaseHandler(handler, correlation)` on the worker side. |
| Request metrics | `ApiObservability(readiness, metrics, correlation)` passed to `ApiApplication`. |
| Health | `ReadinessProbe((TcpHealthCheck("postgres", host, 5432), TcpHealthCheck("rabbitmq", host, 5672), ToolchainHealthCheck()))`. |
| Service spans | `TracedStartPipeline`, `TracedRunPhase`, `TracedDispatchOutbox` wrap the services. |
| Crash alerts | `ProcessCrashHooks().install()`, once per process. |
| Worker liveness | `WorkerHeartbeat(metrics, alerts).start()`, `.record_progress()` per job, `.stop()`. |

### Endpoints

| Path | Auth | Purpose |
|---|---|---|
| `GET /health/live` | none | Always `{"status": "alive"}` while the process runs. |
| `GET /health/ready` | none | `200 {"status": "ready"}` or `503 {"status": "unavailable"}`. It never names the failing dependency; that is in `/metrics` and the logs. |
| `GET /metrics` | API key | Prometheus text format. Give the scraper a bearer token. |

### Correlation

Every request gets one id. It is the trace id of an inbound `traceparent`, else a
well-formed `X-Request-ID` (8 to 64 characters of `A-Z a-z 0-9 . _ -`), else a new
random one. Anything else is replaced, never echoed, because the id lands in every
log line. The id is returned in `X-Request-ID`, copied into each queued job's
`correlation_id` (and a `traceparent` when it is a 32-hex trace id), restored by the
worker, and sent on outbound webhooks as `X-Request-ID` and `traceparent`.

### Alerts and dead letters

A webhook that fails is retried on every dispatch and counted. After
`max_attempts` (default 5) it is dead-lettered, which stops retries, increments
`webhook.dead_lettered` and raises an `error` alert. One bad event never blocks the
events behind it.

`vibey_bootstrap` sends only `CRITICAL` alerts at once, holds `ERROR` and `WARN`
in a digest that nothing here drains, and only records alerts when no recipients
are configured. So `BootstrapAlertDispatcher` always writes the alert to the log
first, at its own level. **Alert on those log lines** (`message` starting with
`alert:`, fields `alert_severity` and `dedup_key`) rather than relying on mail.

The outbox table gained a `dead_at` column. There is no migration tool yet:
recreate any database created before this change.

### Limits to know

- Log masking is by field name. A secret written into the message text itself is
  not masked, so pass values as `extra` fields.
- Counters and latencies are per process. Scrape every replica.
- `ToolchainHealthCheck` and `TcpHealthCheck` check presence and reachability,
  not that the dependency is healthy. There is no LLM-runner check and no budget
  alert yet, because no budget guard exists in this package.
- Entry points that start the API and worker are not part of this package yet, so
  nothing builds this wiring for you.
