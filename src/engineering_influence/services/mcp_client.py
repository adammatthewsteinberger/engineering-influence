# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A minimal Model Context Protocol client: initialize, list the tools, call a tool."""

import json
import re
from collections.abc import Mapping
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
from engineering_influence.models.mcp_call_result import McpCallResult
from engineering_influence.models.mcp_server_info import McpServerInfo
from engineering_influence.models.mcp_tool_descriptor import McpToolDescriptor
from engineering_influence.models.mcp_tool_set import McpToolSet
from engineering_influence.services.interfaces.mcp_client_interface import McpClientInterface


class McpClient(McpClientInterface):
    """JSON-RPC 2.0 over a transport, written from the protocol's published shape.

    It has been tested against a fake transport and, in a later slice, against a small server
    written for the tests; it has not been run against third-party MCP servers.

    **It offers the server nothing.** It announces no capabilities, so a well-behaved server asks
    for none, and a request a server sends anyway is refused (``-32601``), except ``ping``. A
    server can therefore not ask this client to sample a model, read a root or prompt a person.
    Everything a server sends is untrusted: a reply that is not the expected shape is an error, a
    chatty server is cut off after ``MAX_UNRELATED`` messages, and a tool's answer is reduced to
    its text, with anything else noted as left out.
    """

    PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
    MAX_PAGES = 20
    MAX_TOOLS = 500
    MAX_UNRELATED = 100
    KIND = re.compile(r"[a-z_]{1,20}")

    def __init__(
        self,
        transport: McpTransportInterface,
        client_name: str,
        client_version: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("a request timeout is more than zero")
        self._transport = transport
        self._info = {"name": client_name, "version": client_version}
        self._timeout = timeout_seconds
        self._last_id = 0

    def initialize(self) -> McpServerInfo:
        """Start the session and return who the server says it is."""
        result = self._request(
            "initialize",
            {
                "protocolVersion": self.PROTOCOLS[0],
                "capabilities": {},
                "clientInfo": self._info,
            },
        )
        protocol = result.get("protocolVersion")
        if protocol not in self.PROTOCOLS:
            raise self._error(
                "MCP_PROTOCOL_UNSUPPORTED",
                f"the server speaks protocol {str(protocol)[:40]!r}; this client speaks "
                f"{', '.join(self.PROTOCOLS)}",
            )
        server = result.get("serverInfo")
        if not isinstance(server, Mapping):
            raise self._invalid("it did not say who it is")
        try:
            info = McpServerInfo(server.get("name"), server.get("version"), protocol)  # type: ignore[arg-type]
        except ValueError as error:
            raise self._invalid("it did not give its name and version") from error
        self._transport.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return info

    def list_tools(self) -> McpToolSet:
        """Every tool the server advertises, following its pages."""
        tools: list[McpToolDescriptor] = []
        cursor: str | None = None
        for _ in range(self.MAX_PAGES):
            result = self._request("tools/list", {} if cursor is None else {"cursor": cursor})
            page = result.get("tools")
            if not isinstance(page, list):
                raise self._invalid("its tool list is not a list")
            tools.extend(self._tool(entry) for entry in page)
            if len(tools) > self.MAX_TOOLS:
                raise self._invalid(f"it advertises more than {self.MAX_TOOLS} tools")
            cursor = result.get("nextCursor")
            if cursor is None:
                return self._set(tools)
            if not isinstance(cursor, str):
                raise self._invalid("its page cursor is not text")
        raise self._invalid(f"its tool list runs past {self.MAX_PAGES} pages")

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> McpCallResult:
        """Call one tool and return its text answer."""
        result = self._request("tools/call", {"name": name, "arguments": dict(arguments)})
        content = result.get("content", [])
        if not isinstance(content, list):
            raise self._invalid("a tool's content is not a list")
        parts = [self._text(block) for block in content]
        if not parts and isinstance(result.get("structuredContent"), (dict, list)):
            parts.append(json.dumps(result["structuredContent"], sort_keys=True))
        return McpCallResult("\n".join(parts), result.get("isError") is True)

    def close(self) -> None:
        """End the session."""
        self._transport.close()

    def _request(self, method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        self._last_id += 1
        ident = self._last_id
        self._transport.send({"jsonrpc": "2.0", "id": ident, "method": method, "params": params})
        for _ in range(self.MAX_UNRELATED + 1):
            message = self._transport.receive(self._timeout)
            if "method" in message:
                self._refuse(message)
            elif message.get("id") == ident:
                return self._result(method, message)
        raise self._invalid(
            f"it sent more than {self.MAX_UNRELATED} messages that were not the answer"
        )

    def _result(self, method: str, message: Mapping[str, Any]) -> Mapping[str, Any]:
        failure = message.get("error")
        if failure is not None:
            detail = failure.get("message") if isinstance(failure, Mapping) else failure
            raise self._error("MCP_SERVER_ERROR", f"{method} failed: {str(detail)[:200]!r}")
        result = message.get("result")
        if not isinstance(result, Mapping):
            raise self._invalid(f"its answer to {method} has no result")
        return result

    def _refuse(self, message: Mapping[str, Any]) -> None:
        """Answer a request the server sent to us: nothing is offered, and only ping is allowed."""
        if "id" not in message:
            return
        if message.get("method") == "ping":
            self._transport.send({"jsonrpc": "2.0", "id": message["id"], "result": {}})
            return
        self._transport.send(
            {
                "jsonrpc": "2.0",
                "id": message["id"],
                "error": {"code": -32601, "message": "method not found"},
            }
        )

    def _tool(self, entry: Any) -> McpToolDescriptor:
        if not isinstance(entry, Mapping):
            raise self._invalid("a tool in its list is not an object")
        description = entry.get("description")
        try:
            return McpToolDescriptor(
                entry.get("name"),  # type: ignore[arg-type]
                "" if description is None else description,
                entry.get("inputSchema"),  # type: ignore[arg-type]
            )
        except (ValueError, TypeError) as error:
            raise self._invalid("a tool in its list is malformed") from error

    def _set(self, tools: list[McpToolDescriptor]) -> McpToolSet:
        try:
            return McpToolSet(tuple(tools))
        except ValueError as error:
            raise self._invalid("it advertises one tool name twice") from error

    def _text(self, block: Any) -> str:
        if isinstance(block, Mapping) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                return text
        kind = block.get("type") if isinstance(block, Mapping) else None
        shown = kind if isinstance(kind, str) and self.KIND.fullmatch(kind) else "unknown"
        return f"[{shown} content omitted]"

    def _invalid(self, why: str) -> ApplicationError:
        return self._error(
            "MCP_REPLY_INVALID", f"the MCP server sent a reply this client cannot use: {why}"
        )

    @staticmethod
    def _error(code: str, message: str) -> ApplicationError:
        return ApplicationError(code=code, message=message, http_status=502)
