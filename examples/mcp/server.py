"""Run the MCP server over stdio, as an MCP host (Claude Desktop, an IDE, an agent) would.

    uv run python examples/mcp/server.py

Register it with a host by pointing the host at that command, for example in Claude
Desktop's `claude_desktop_config.json`:

    {"mcpServers": {"engineering-influence": {
        "command": "uv", "args": ["run", "python", "examples/mcp/server.py"],
        "cwd": "/path/to/engineering-influence"}}}

The server uses in-memory adapters, so it plans a pipeline but does not reach the stack.
It is a local process and is not authenticated: never expose it on a network.
"""

from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interaction.mcp.application import McpApplication

if __name__ == "__main__":
    McpApplication(InMemoryLedger(), InMemoryQueue()).build().run("stdio")
