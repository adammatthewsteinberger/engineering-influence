# ADR 0007: Models are called over plain httpx, behind `ModelInterface`

Status: accepted

## Context

M5 needs adapters for Anthropic and for OpenAI-compatible servers (which also covers local
models). The lock already contains the `anthropic` and `openai` SDKs, but only as transitive
dependencies of `vibey-engine`, at the versions that package pins. `httpx` is already a direct
dependency of the `webhooks` extra.

## Decision

1. **Adapters use `httpx` directly**, not the vendor SDKs. Both APIs are one JSON `POST` for a
   completion and one for a token count.
2. **The transport is injected.** An adapter takes an `httpx.Client` in its constructor, so tests
   pass one built on `httpx.MockTransport` and record cassettes without patching, as
   `tests/architecture/test_no_patching.py` requires.
3. **Retry classification stays ours.** An adapter maps status codes onto `TransientStageError`
   (timeout, 429 without a spent-credit body, 5xx), `CapacityExhaustedError` (credit gone, 401/403)
   or an unrecoverable error, so the run machinery never sees a vendor exception.
4. **The domain types are vendor-neutral**: `ModelRequest`, `ModelResponse`, `ModelUsage` and
   `ProviderDescriptor`, with integer micro-dollar prices that round up.

## Consequences

- The runtime dependency set does not grow, and a `vibey-engine` repin cannot change what the
  adapters send.
- We own request shaping, header handling, prompt-cache markers and response parsing, and must
  track API changes ourselves. Cassettes recorded from synthetic briefs and a `paid` marker for
  live checks keep that honest.
- Streaming is not used: a book stage waits for a whole response, and the run journal stores the
  whole response.
