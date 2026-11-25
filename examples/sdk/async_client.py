"""Start several pipelines concurrently with the asynchronous Python SDK.

    uv sync --extra test
    set -a; . examples/.env; set +a
    uv run python examples/sdk/async_client.py

Needs EI_API_KEY; EI_BASE_URL defaults to the local compose stack.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from engineering_influence_sdk import AsyncEngineeringInfluenceClient

PROJECT = json.loads(
    (Path(__file__).parents[1] / "sample_project" / "project.json").read_text(encoding="utf-8")
)


async def main() -> int:
    api_key = os.environ.get("EI_API_KEY")
    if not api_key:
        print("set EI_API_KEY (see examples/.env)", file=sys.stderr)
        return 2
    client = AsyncEngineeringInfluenceClient(
        os.environ.get("EI_BASE_URL", "http://127.0.0.1:8000"), api_key
    )
    try:
        results = await asyncio.gather(
            *(
                client.start_pipeline(
                    f"{PROJECT['slug']}-{number}",
                    f"{PROJECT['title']} {number}",
                    tuple(PROJECT["postulates"]),
                    tuple(PROJECT["stages"]),
                )
                for number in (1, 2, 3)
            )
        )
    finally:
        await client.close()
    for started in results:
        print(json.dumps(started, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
