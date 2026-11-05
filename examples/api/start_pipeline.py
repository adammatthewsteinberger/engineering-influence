# /// script
# requires-python = ">=3.12"
# dependencies = ["requests>=2.32,<3"]
# ///
"""Start a pipeline over REST, the way any HTTP client would.

    sh examples/up.sh && set -a && . examples/.env && set +a
    uv run examples/api/start_pipeline.py

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
        print("set EI_API_KEY (see examples/.env) and, if needed, EI_BASE_URL", file=sys.stderr)
        return 2

    # Probes need no key: use them to wait for the stack, or as a load balancer check.
    ready = requests.get(f"{BASE_URL}/health/ready", timeout=5)
    print(f"ready: {ready.status_code} {ready.json()['status']}")

    # The pipeline endpoint is guarded and fails closed.
    anonymous = requests.post(f"{BASE_URL}/v1/pipelines", json=PROJECT, timeout=5)
    print(f"without a key: {anonymous.status_code}")

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {API_KEY}"  # or: X-API-Key: <key>
    session.headers["X-Request-ID"] = "example-api-0001"  # optional; echoed back and logged

    response = session.post(f"{BASE_URL}/v1/pipelines", json=PROJECT, timeout=10)
    response.raise_for_status()
    print(f"started: {response.status_code} {json.dumps(response.json(), sort_keys=True)}")
    print(f"correlation id: {response.headers['X-Request-ID']}")

    # A bad request is rejected by validation before anything is queued.
    invalid = session.post(f"{BASE_URL}/v1/pipelines", json={"slug": "x"}, timeout=10)
    print(f"invalid body: {invalid.status_code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
