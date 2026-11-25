#!/bin/sh
# The same calls with curl. Needs curl and the variables from examples/.env:
#
#   set -a; . examples/.env; set +a
#   sh examples/api/run.sh
set -eu

: "${EI_API_KEY:?set EI_API_KEY (source examples/.env)}"
BASE="${EI_BASE_URL:-http://127.0.0.1:8000}"
BODY="$(dirname "$0")/../sample_project/project.json"

echo "== probes need no key"
curl -fsS "$BASE/health/live"; echo
curl -fsS "$BASE/health/ready"; echo

echo "== the API is guarded (expect 401)"
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$BASE/v1/pipelines" \
  -H 'Content-Type: application/json' --data @"$BODY"

echo "== start a pipeline"
curl -fsS -X POST "$BASE/v1/pipelines" \
  -H "Authorization: Bearer $EI_API_KEY" \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: example-curl-0001' \
  --data @"$BODY"; echo

echo "== Prometheus metrics (a key is required)"
curl -fsS "$BASE/metrics" -H "Authorization: Bearer $EI_API_KEY" | grep -m3 http_requests || true
