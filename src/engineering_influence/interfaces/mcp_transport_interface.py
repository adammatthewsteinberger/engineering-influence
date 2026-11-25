# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: one conversation with an MCP server."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class McpTransportInterface(ABC):
    """Carries JSON-RPC messages to and from one MCP server, and nothing else."""

    __slots__ = ()

    @abstractmethod
    def send(self, message: Mapping[str, Any]) -> None:
        """Send one message. Raise ``ApplicationError`` if the server is gone."""

    @abstractmethod
    def receive(self, timeout_seconds: float) -> Mapping[str, Any]:
        """The next message from the server.

        Raise ``TransientStageError`` when none arrives in time and ``ApplicationError`` when the
        server has gone or sent something that is not a JSON object. What it sends is untrusted.
        """

    @abstractmethod
    def close(self) -> None:
        """End the conversation and stop whatever carries it. Safe to call twice."""
