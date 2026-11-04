"""Async SDK example against the in-process ASGI application."""

import asyncio

import httpx
from _sample import SampleGuard, SampleProject
from engineering_influence_sdk import AsyncEngineeringInfluenceClient

from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interaction.api.application import ApiApplication


async def main() -> None:
    app = ApiApplication(InMemoryLedger(), InMemoryQueue(), SampleGuard().build()).build()
    project = SampleProject().load()
    client = AsyncEngineeringInfluenceClient(
        "http://local", SampleGuard.API_KEY, httpx.ASGITransport(app=app)
    )
    print(
        await client.start_pipeline(
            project["slug"],
            project["title"],
            tuple(project["postulates"]),
            tuple(project["stages"]),
        )
    )
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
