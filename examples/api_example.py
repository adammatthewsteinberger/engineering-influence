"""REST example: call POST /v1/pipelines against an in-process ASGI app."""

from _sample import SampleGuard, SampleProject
from fastapi.testclient import TestClient

from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interaction.api.application import ApiApplication


def main() -> None:
    app = ApiApplication(InMemoryLedger(), InMemoryQueue(), SampleGuard().build()).build()
    client = TestClient(app)
    refused = client.post("/v1/pipelines", json=SampleProject().load())
    print("without a key:", refused.status_code)
    response = client.post(
        "/v1/pipelines",
        json=SampleProject().load(),
        headers={"Authorization": f"Bearer {SampleGuard.API_KEY}"},
    )
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    main()
