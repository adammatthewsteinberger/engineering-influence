"""MCP example: invoke the start_pipeline tool on the FastMCP server."""

import asyncio

from _sample import SampleProject

from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interaction.mcp.application import McpApplication


async def main() -> None:
    server = McpApplication(InMemoryLedger(), InMemoryQueue()).build()
    result = await server.call_tool("start_pipeline", SampleProject().load())
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
