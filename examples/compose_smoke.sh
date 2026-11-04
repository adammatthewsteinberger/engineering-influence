#!/bin/sh
# Bring the whole stack up with throwaway credentials, run a two-stage pipeline through it,
# prove a malformed message is dead-lettered, and tear everything down.
set -eu

cd "$(dirname "$0")"
PROJECT="ei-smoke-$$"
PORT="${EI_SMOKE_PORT:-18080}"
ENV_FILE="$(mktemp)"
compose() { docker compose -p "$PROJECT" -f docker-compose.yml --env-file "$ENV_FILE" "$@"; }
cleanup() {
  compose logs --no-color --tail 40 api worker 2>/dev/null || true
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  rm -f "$ENV_FILE"
}
trap cleanup EXIT

secret() { python3 -c 'import secrets; print(secrets.token_hex(16))'; }
KEY="$(secret)$(secret)"
printf 'POSTGRES_PASSWORD=%s\nRABBITMQ_PASSWORD=%s\nEI_API_KEYS=%s\nEI_API_PORT=%s\n' \
  "$(secret)" "$(secret)" "$KEY" "$PORT" > "$ENV_FILE"

echo "== refuses to start without credentials"
if docker compose -p "$PROJECT-nocreds" -f docker-compose.yml config >/dev/null 2>&1; then
  echo "FAIL: compose accepted an empty environment" >&2
  exit 1
fi
echo "ok"

echo "== up"
compose up -d --build --wait

BASE="http://127.0.0.1:$PORT"
echo "== probes need no key"
curl -fsS "$BASE/health/live" | grep -q alive
curl -fsS "$BASE/health/ready" | grep -q ready
echo "ok"

echo "== the API is guarded"
test "$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/v1/pipelines")" = 401
test "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/metrics")" = 401
echo "ok"

echo "== a two-stage pipeline runs to completion"
RESPONSE="$(curl -fsS -X POST "$BASE/v1/pipelines" \
  -H "Authorization: Bearer $KEY" -H 'X-Request-ID: smoke-request-0001' \
  -H 'Content-Type: application/json' \
  -d '{"slug":"smoke","title":"Smoke","postulates":["Evidence first."],"stages":["thesis","book"]}')"
echo "$RESPONSE"
events() { compose exec -T postgres psql -U ei -d ei -tAc 'select event_name from ledgereventrecord order by id'; }
for _ in $(seq 1 60); do
  if events | grep -q '^pipeline.completed$'; then break; fi
  sleep 1
done
ACTUAL="$(events | tr '\n' ' ')"
EXPECTED="pipeline.started phase.completed phase.completed pipeline.completed "
if [ "$ACTUAL" != "$EXPECTED" ]; then
  echo "FAIL: ledger was '$ACTUAL', expected '$EXPECTED'" >&2
  exit 1
fi
echo "ok: $ACTUAL"

echo "== the correlation id survived the broker"
compose logs --no-color worker | grep -q smoke-request-0001
echo "ok"

echo "== a malformed message is dead-lettered, not retried"
compose exec -T api python - <<'PY'
import asyncio, os, aio_pika

async def main():
    connection = await aio_pika.connect_robust(os.environ["EI_RABBITMQ_URL"])
    async with connection:
        channel = await connection.channel()
        await channel.default_exchange.publish(
            aio_pika.Message(body=b"not a job"), routing_key="engineering-influence.jobs"
        )

asyncio.run(main())
PY
for _ in $(seq 1 30); do
  DEAD="$(compose exec -T rabbitmq rabbitmqctl list_queues name messages | awk '$1=="engineering-influence.jobs.dead"{print $2}')"
  if [ "${DEAD:-0}" -ge 1 ]; then break; fi
  sleep 1
done
test "${DEAD:-0}" -ge 1
echo "ok: $DEAD dead-lettered"

echo "== the worker is still alive and the API still ready"
curl -fsS "$BASE/health/ready" | grep -q ready
test -n "$(compose ps --status running -q worker)"
echo "ok"

echo "SMOKE PASSED"
