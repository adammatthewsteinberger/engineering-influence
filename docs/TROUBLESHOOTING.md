# Troubleshooting

Find the symptom, then the cause. Commands assume you ran `set -a; . examples/.env; set +a`.

| Symptom | Cause | Fix |
|---|---|---|
| `docker compose` says `set POSTGRES_PASSWORD in examples/.env` | Compose has no default credentials by design | `sh examples/up.sh` generates `examples/.env`, or copy `.env.example` and fill every blank |
| `error: required secret EI_DATABASE_URL is not configured` (exit 2) | `ei serve` fails closed without settings | Export the variables in [CONFIGURATION.md](CONFIGURATION.md#running-the-stack) |
| `ei serve` prints `needs the api and runtime extras` | Optional dependencies missing | `pip install "engineering-influence[api,runtime]"` or `uv sync --extra api --extra runtime` |
| `ei book …` prints `needs the publishing extra` | Pillow, numpy and the PDF libraries are optional | `pip install "engineering-influence[publishing]"` |
| API will not start; mentions API keys | `EI_API_KEYS` unset or a key shorter than 24 characters | `openssl rand -hex 24` per key |
| `401 UNAUTHORIZED` | Missing or wrong key | `Authorization: Bearer $EI_API_KEY` or `X-API-Key`; the key is the one in `EI_API_KEYS` |
| `429 RATE_LIMITED` | Budget spent (default burst 30, 10 per second) | Back off; raise `EI_RATE_BURST` / `EI_RATE_PER_SECOND` for trusted clients |
| `422` on `POST /v1/pipelines` | A required field is missing or a stage name is unknown | Valid stages: `thesis book novel screenplay hub spokes distribution publish` |
| `GET /health/ready` returns 503 | A dependency is unreachable; the body never says which | Read `/metrics` (needs a key) and the API log |
| `Connection refused` on port 8000 | Stack not up, or `EI_API_PORT` changed | `docker compose -f examples/docker-compose.yml --env-file examples/.env ps` |
| Postgres container unhealthy, exits at start (Postgres 18 image) | The volume is mounted at `/var/lib/postgresql/data`; 18+ images keep a versioned directory under `/var/lib/postgresql` | Mount `/var/lib/postgresql` (the shipped compose file does) and delete the old volume: `sh examples/down.sh --volumes` |
| `api` or `worker` logs `UniqueViolation … pg_type_typname_nsp_index` once at start | Both create tables on an empty database at the same moment; one loses the race and restarts | Harmless: `restart: unless-stopped` recovers it. Start `postgres`, then `api`, then `worker` to avoid it |
| A job sits in `engineering-influence.jobs.dead` | The job was malformed or failed; nothing retries it | Inspect it in the RabbitMQ UI or `rabbitmqctl`, fix the cause, republish by hand |
| A stage ran twice | At-least-once delivery: the worker died between the ledger write and the acknowledgement | Make downstream consumers idempotent on `job_id` |
| Pipeline stops at `gate.awaiting` | A human gate (or a rejecting gate) parked it; no endpoint resolves gates yet | Not recoverable through the API yet |
| MCP host shows no tools | It launched the wrong command or directory | Run `uv run python examples/mcp/client.py` to prove the server; give the host the same command and `cwd` |
| Webhook receiver answers 401 | Wrong secret, body re-serialised before verifying, or clock skew over 300 seconds | Sign and verify the **raw bytes**; sync the clock |
| Webhook receiver answers 409 | Replay: the same signature arrived twice | Expected on retries after your `2xx`; treat as already processed |
| `ModuleNotFoundError: mcp.server.fastmcp` | You installed `mcp` 1.x with this release | This project needs `mcp>=2,<3`; `pip install -U "mcp>=2,<3"` |
| `ruff`, `mypy` or `pytest` not found | Wrong extras | `uv sync --extra test --extra runtime --extra dev --extra publishing` |
| Coverage drops below 100% only for `book_cli` / `serve_cli` | Child-process coverage not enabled (pytest-cov 7+) | Keep `patch = ["subprocess"]` and `parallel = true` in `[tool.coverage.run]` |
| Pushed a Dependabot-style commit and `provenance` fails | The commit has no `Made-With:` trailer | `vibey-gh install` adds the commit hook; amend the commit message |

## Collecting evidence for a bug report

```bash
uv run ei --version
docker compose -f examples/docker-compose.yml --env-file examples/.env ps
docker compose -f examples/docker-compose.yml --env-file examples/.env logs --no-color --tail 100 api worker
```

Logs are JSON lines with a `correlation_id`; search for the id from your `X-Request-ID`.
Secrets are masked by field name, but check before pasting. Report security issues privately
through [SECURITY.md](../SECURITY.md), not in a public issue.
