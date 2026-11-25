# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A minimal Model Context Protocol client: initialize, list the tools, call a tool, read a resource."""

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

    **Resources are reached as two tools it adds itself.** When a server declares the ``resources`` capability, and has
    no tool of those names, ``list_tools`` ends with ``list_resources`` and ``read_resource``, whose descriptions and
    schemas are fixed here and not the server's. Because they are in the tool list they are pinned by the same hash, can
    be granted to a stage only by name like any other tool, and are offered to no stage by default. ``call_tool`` on either
    name sends ``resources/list`` or ``resources/read`` and returns text: a binary resource is noted as left out, a list
    is cut at 200 entries, and a uri must be one line of at most 2,000 characters. Nothing is subscribed to.
    """

    PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
    MAX_PAGES = 20
    MAX_TOOLS = 500
    MAX_UNRELATED = 100
    KIND = re.compile(r"[a-z_]{1,20}")
    LIST_RESOURCES = "list_resources"
    READ_RESOURCE = "read_resource"
    MAX_RESOURCES = 200
    MAX_URI_CHARS = 2_000
    RESOURCE_TOOLS = (
        McpToolDescriptor(
            LIST_RESOURCES,
            "Lists the resources this server offers, one line each: its uri, then its name and type. "
            "Read one with read_resource.",
            {"type": "object", "properties": {}, "additionalProperties": False},
        ),
        McpToolDescriptor(
            READ_RESOURCE,
            "Reads the text of one resource of this server, by the uri that list_resources gave.",
            {
                "type": "object",
                "properties": {"uri": {"type": "string", "maxLength": MAX_URI_CHARS}},
                "required": ["uri"],
                "additionalProperties": False,
            },
        ),
    )

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
        self._resources = False
        self._synthetic: frozenset[str] = frozenset()

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
        capabilities = result.get("capabilities")
        self._resources = isinstance(capabilities, Mapping) and isinstance(
            capabilities.get("resources"), Mapping
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
                return self._set(self._with_resources(tools))
            if not isinstance(cursor, str):
                raise self._invalid("its page cursor is not text")
        raise self._invalid(f"its tool list runs past {self.MAX_PAGES} pages")

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> McpCallResult:
        """Call one tool and return its text answer."""
        if name in self._synthetic:
            return self._resource(name, arguments)
        result = self._request("tools/call", {"name": name, "arguments": dict(arguments)})
        content = result.get("content", [])
        if not isinstance(content, list):
            raise self._invalid("a tool's content is not a list")
        parts = [self._text(block) for block in content]
        if not parts and isinstance(result.get("structuredContent"), (dict, list)):
            parts.append(json.dumps(result["structuredContent"], sort_keys=True))
        return McpCallResult("\n".join(parts), result.get("isError") is True)

    def _with_resources(self, tools: list[McpToolDescriptor]) -> list[McpToolDescriptor]:
        reserved = {self.LIST_RESOURCES, self.READ_RESOURCE}
        if not self._resources or reserved & {tool.name for tool in tools}:
            self._synthetic = frozenset()
            return tools
        self._synthetic = frozenset(reserved)
        return [*tools, *self.RESOURCE_TOOLS]

    def _resource(self, name: str, arguments: Mapping[str, Any]) -> McpCallResult:
        if name == self.LIST_RESOURCES:
            return McpCallResult(self._resource_list(), False)
        uri = arguments.get("uri")
        if (
            not isinstance(uri, str)
            or not uri
            or len(uri) > self.MAX_URI_CHARS
            or not uri.isprintable()
        ):
            return McpCallResult("the uri is one line of text, as list_resources gave it", True)
        result = self._request("resources/read", {"uri": uri})
        contents = result.get("contents")
        if not isinstance(contents, list):
            raise self._invalid("a resource's contents are not a list")
        parts = [
            block["text"]
            if isinstance(block, Mapping) and isinstance(block.get("text"), str)
            else "[binary content omitted]"
            for block in contents
        ]
        return McpCallResult("\n".join(parts), False)

    def _resource_list(self) -> str:
        lines: list[str] = []
        more = 0
        cursor: str | None = None
        for _ in range(self.MAX_PAGES):
            result = self._request("resources/list", {} if cursor is None else {"cursor": cursor})
            page = result.get("resources")
            if not isinstance(page, list):
                raise self._invalid("its resource list is not a list")
            for entry in page:
                line = self._resource_line(entry)
                if len(lines) < self.MAX_RESOURCES:
                    lines.append(line)
                else:
                    more += 1
            cursor = result.get("nextCursor")
            if cursor is None:
                shown = "\n".join(lines) or "the server lists no resources"
                return shown + (f"\n[{more} more resources not shown]" if more else "")
            if not isinstance(cursor, str):
                raise self._invalid("its page cursor is not text")
        raise self._invalid(f"its resource list runs past {self.MAX_PAGES} pages")

    def _resource_line(self, entry: Any) -> str:
        uri = entry.get("uri") if isinstance(entry, Mapping) else None
        if (
            not isinstance(uri, str)
            or not uri
            or len(uri) > self.MAX_URI_CHARS
            or not uri.isprintable()
        ):
            raise self._invalid("a resource in its list is malformed")
        name = self._flat(entry.get("name"), 100)
        kind = self._flat(entry.get("mimeType"), 60)
        return uri + (f" - {name}" if name else "") + (f" ({kind})" if kind else "")

    @staticmethod
    def _flat(value: Any, limit: int) -> str:
        if not isinstance(value, str):
            return ""
        return " ".join("".join(c if c.isprintable() else " " for c in value).split())[:limit]

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
