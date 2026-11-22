# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads the message events out of a Server-Sent Events stream, a few bytes at a time."""

from engineering_influence.infrastructure.tools.interfaces.sse_event_reader_interface import (
    SseEventReaderInterface,
)


class SseEventReader(SseEventReaderInterface):
    """The part of the SSE format a Streamable HTTP MCP server uses, with every line bounded.

    - Lines end with ``\\n`` or ``\\r\\n``; a blank line ends an event. (A bare carriage return as a
      line ending is not recognised: servers do not send it.)
    - An event's data is its ``data:`` lines joined with a newline. Only events with no ``event:``
      name or the name ``message`` are returned; others are skipped, as are comments, ``id:``,
      ``retry:`` and unknown fields.
    - An event the stream ends in the middle of is dropped, as the format says.
    - A line longer than ``max_line_bytes`` is an error whether or not it is finished, so a server
      cannot make this buffer grow by never ending a line. What the server sends is untrusted.
    """

    def __init__(self, max_line_bytes: int) -> None:
        if max_line_bytes < 1:
            raise ValueError("a line may be at least one byte long")
        self._max = max_line_bytes
        self._buffer = bytearray()
        self._data: list[str] = []
        self._event = ""

    def feed(self, chunk: bytes) -> list[str]:
        """Take the next bytes; return the data of every message event they completed, in order."""
        self._buffer.extend(chunk)
        found: list[str] = []
        while (end := self._buffer.find(b"\n")) >= 0:
            line = bytes(self._buffer[:end]).removesuffix(b"\r")
            del self._buffer[: end + 1]
            self._line(line, found)
        if len(self._buffer) > self._max:
            raise ValueError(f"an event line is longer than {self._max} bytes")
        return found

    def _line(self, line: bytes, found: list[str]) -> None:
        if len(line) > self._max:
            raise ValueError(f"an event line is longer than {self._max} bytes")
        if not line:
            if self._data and self._event in ("", "message"):
                found.append("\n".join(self._data))
            self._data = []
            self._event = ""
            return
        name, _, value = line.partition(b":")
        if name not in (b"data", b"event"):
            return
        text = value.removeprefix(b" ").decode("utf-8")
        if name == b"data":
            self._data.append(text)
        else:
            self._event = text
