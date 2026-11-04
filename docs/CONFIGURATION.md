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
