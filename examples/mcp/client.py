"""Talk to the MCP server the way a host does: spawn it over stdio, list tools, call one.

uv run python examples/mcp/client.py
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

PROJECT = json.loads(
    (Path(__file__).parents[1] / "sample_project" / "project.json").read_text(encoding="utf-8")
)


async def main() -> int:
    server = StdioServerParameters(
        command=sys.executable, args=[str(Path(__file__).with_name("server.py"))]
    )
    async with Client(server) as client:
        listing = await client.list_tools()
        for tool in listing.tools:
            print(f"tool: {tool.name} - {tool.description}")
        result = await client.call_tool("start_pipeline", PROJECT)
        if result.is_error:
            print(f"tool error: {result.content}", file=sys.stderr)
            return 1
        print(json.dumps(result.structured_content, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
