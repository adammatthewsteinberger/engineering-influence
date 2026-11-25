# /// script
# requires-python = ">=3.12"
# dependencies = ["requests>=2.32,<3"]
# ///
"""Check health, follow a correlation id, and scrape Prometheus metrics, as an operator would.

    set -a; . examples/.env; set +a
    uv run examples/observability/scrape.py

Needs EI_API_KEY; EI_BASE_URL defaults to the local compose stack.
"""

import json
import os
import sys
from pathlib import Path

import requests

BASE_URL = os.environ.get("EI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.environ.get("EI_API_KEY")
PROJECT = json.loads(
    (Path(__file__).parents[1] / "sample_project" / "project.json").read_text(encoding="utf-8")
)


def main() -> int:
    if not API_KEY:
        print("set EI_API_KEY (see examples/.env)", file=sys.stderr)
        return 2
    auth = {"Authorization": f"Bearer {API_KEY}"}

    print("live: ", requests.get(f"{BASE_URL}/health/live", timeout=5).json()["status"])
    ready = requests.get(f"{BASE_URL}/health/ready", timeout=5)
    print("ready:", ready.status_code, ready.json()["status"])  # 503 when a dependency is down

    # One id follows the request through the API, the queue, the worker and any webhook.
    # Find it in the logs: docker compose -f examples/docker-compose.yml logs api worker
    reply = requests.post(
        f"{BASE_URL}/v1/pipelines",
        json=PROJECT,
        headers={**auth, "X-Request-ID": "example-observe-0001"},
        timeout=10,
    )
    reply.raise_for_status()
    print("request id echoed:", reply.headers["X-Request-ID"])

    # /metrics is guarded like the API: give your scraper a bearer token.
    print("metrics without a key:", requests.get(f"{BASE_URL}/metrics", timeout=5).status_code)
    metrics = requests.get(f"{BASE_URL}/metrics", headers=auth, timeout=5)
    metrics.raise_for_status()
    for line in metrics.text.splitlines():
        if line.startswith("#") or "http_requests" not in line:
            continue
        print("metric:", line)
        break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
