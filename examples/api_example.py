"""REST example: call POST /v1/pipelines against an in-process ASGI app."""

from _sample import SampleProject
from fastapi.testclient import TestClient

from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interaction.api.application import ApiApplication


def main() -> None:
    app = ApiApplication(InMemoryLedger(), InMemoryQueue()).build()
    response = TestClient(app).post("/v1/pipelines", json=SampleProject().load())
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    main()
