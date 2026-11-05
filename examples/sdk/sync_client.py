"""Start a pipeline with the synchronous Python SDK.

    uv sync --extra test            # installs the SDK from this repository
    set -a; . examples/.env; set +a
    uv run python examples/sdk/sync_client.py

Needs EI_API_KEY; EI_BASE_URL defaults to the local compose stack.
"""

import json
import os
import sys
from pathlib import Path

import httpx
from engineering_influence_sdk import EngineeringInfluenceClient

PROJECT = json.loads(
    (Path(__file__).parents[1] / "sample_project" / "project.json").read_text(encoding="utf-8")
)


def main() -> int:
    api_key = os.environ.get("EI_API_KEY")
    if not api_key:
        print("set EI_API_KEY (see examples/.env)", file=sys.stderr)
        return 2
    client = EngineeringInfluenceClient(
        os.environ.get("EI_BASE_URL", "http://127.0.0.1:8000"), api_key
    )
    try:
        started = client.start_pipeline(
            PROJECT["slug"],
            PROJECT["title"],
            tuple(PROJECT["postulates"]),
            tuple(PROJECT["stages"]),
        )
        print(json.dumps(started, sort_keys=True))
    except httpx.HTTPStatusError as error:
        # The SDK raises for any non-2xx answer; the body is the API's error document.
        print(f"rejected: {error.response.status_code} {error.response.text}", file=sys.stderr)
        return 1
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
