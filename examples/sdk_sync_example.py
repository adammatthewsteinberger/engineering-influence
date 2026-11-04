"""Sync SDK example, wired to the in-process app through an ASGI-backed transport."""

import httpx
from _sample import SampleGuard, SampleProject
from engineering_influence_sdk import EngineeringInfluenceClient
from fastapi.testclient import TestClient

from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interaction.api.application import ApiApplication


def main() -> None:
    app = ApiApplication(InMemoryLedger(), InMemoryQueue(), SampleGuard().build()).build()
    server = TestClient(app)

    def handler(request: httpx.Request) -> httpx.Response:
        forwarded = server.post(
            request.url.path,
            content=request.content,
            headers={
                "content-type": "application/json",
                "authorization": request.headers["authorization"],
            },
        )
        return httpx.Response(forwarded.status_code, json=forwarded.json(), request=request)

    project = SampleProject().load()
    client = EngineeringInfluenceClient(
        "http://local", SampleGuard.API_KEY, httpx.MockTransport(handler)
    )
    print(
        client.start_pipeline(
            project["slug"],
            project["title"],
            tuple(project["postulates"]),
            tuple(project["stages"]),
        )
    )
    client.close()


if __name__ == "__main__":
    main()
