# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One MCP server run as a child process, talked to over its standard input and output."""

import contextlib
import json
import os
import queue
import shutil
import signal
import subprocess  # nosec B404
import threading
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import IO, Any, cast

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.process.interfaces.process_meter_interface import (
    ProcessMeterInterface,
)
from engineering_influence.infrastructure.process.process_meter import ProcessMeter
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
from engineering_influence.models.tool_limits import ToolLimits


class StdioMcpTransport(McpTransportInterface):
    """Newline-delimited JSON messages to and from a server that lives in its own process group.

    - **Started once, stopped for good.** The server gets its own session, so it and everything it
      starts share a process group. ``close`` kills the whole group, then reaps the leader. The
      leader is never reaped earlier, so its id is still ours when the group is killed and cannot
      have been given to a stranger: this is why exit is noticed by the output ending, not by polling,
      and why a second ``close`` signals nothing.
    - **Limits as for the build tools.** A watchdog samples resident memory (the whole group) and the
      size of the server's working directory every ``sample_seconds``, and stops the server when it
      passes ``limits.max_memory_bytes`` or ``limits.max_disk_bytes``, or has run for
      ``limits.timeout_seconds`` in all. A limit is enforced to within what the server can allocate or
      write in one interval, and only the working directory counts for disk.
    - **A line is bounded and a flood is slowed.** A line over ``MAX_LINE_BYTES`` stops the server.
      Lines wait in a short queue, so a server that talks faster than it is read blocks on its own pipe.
    - **Its error output is kept, not trusted.** Standard error is drained so a chatty server cannot
      block, and its last 2000 bytes are quoted when the server dies.
    - This needs process groups: Linux and macOS, not Windows.
    """

    MAX_LINE_BYTES = 4 * 1024 * 1024
    TAIL_BYTES = 2000
    SHOWN_CHARACTERS = 500
    QUEUE_LINES = 64
    JOIN_SECONDS = 2.0

    def __init__(
        self,
        command: tuple[str, ...],
        env: Mapping[str, str],
        limits: ToolLimits,
        workdir: Path,
        meter: ProcessMeterInterface | None = None,
        sample_seconds: float = 0.5,
        kill_group: Callable[[int, int], None] | None = None,
    ) -> None:
        if sample_seconds <= 0:
            raise ValueError("the sampling interval is more than zero")
        self._limits = limits
        self._workdir = workdir
        self._meter = meter or ProcessMeter()
        self._sample_seconds = sample_seconds
        self._kill_group = kill_group or os.killpg
        self._lines: queue.Queue[bytes | None] = queue.Queue(maxsize=self.QUEUE_LINES)
        self._stopped = threading.Event()
        self._guard = threading.Lock()
        self._violation: str | None = None
        self._tail = b""
        self._closed = False
        self._process = self._start(command, env, workdir)
        self._stdin = cast(IO[bytes], self._process.stdin)
        self._stdout = cast(IO[bytes], self._process.stdout)
        self._stderr = cast(IO[bytes], self._process.stderr)
        self._threads = [
            threading.Thread(target=self._read_stdout, daemon=True, name="mcp-stdout"),
            threading.Thread(target=self._read_stderr, daemon=True, name="mcp-stderr"),
            threading.Thread(target=self._watch, daemon=True, name="mcp-watchdog"),
        ]
        for thread in self._threads:
            thread.start()

    def send(self, message: Mapping[str, Any]) -> None:
        """Send one message. Raise ``ApplicationError`` if the server is gone."""
        data = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            self._stdin.write(data)
            self._stdin.flush()
        except (OSError, ValueError) as error:
            raise self._gone() from error

    def receive(self, timeout_seconds: float) -> Mapping[str, Any]:
        """The next message from the server, or an error saying why there is none."""
        try:
            line = self._lines.get(timeout=timeout_seconds)
        except queue.Empty as error:
            raise TransientStageError(
                f"the MCP server did not answer within {timeout_seconds:g} seconds"
            ) from error
        if line is None:
            self._lines.put_nowait(None)  # the end of the output stays the end
            raise self._gone()
        try:
            message = json.loads(line)
        except (ValueError, RecursionError) as error:
            raise self._invalid("a line that is not JSON") from error
        if not isinstance(message, dict):
            raise self._invalid("JSON that is not an object")
        return message

    def close(self) -> None:
        """Kill the server and everything it started, reap it and remove its directory. Safe twice."""
        if self._closed:
            return
        self._closed = True
        self._stopped.set()
        self._kill()
        for thread in self._threads:
            thread.join(self.JOIN_SECONDS)
        self._process.wait()
        for pipe in (self._stdin, self._stdout, self._stderr):
            with contextlib.suppress(OSError):  # a dead server's stdin may still hold unsent bytes
                pipe.close()
        shutil.rmtree(self._workdir, ignore_errors=True)

    @staticmethod
    def _start(
        command: tuple[str, ...], env: Mapping[str, str], workdir: Path
    ) -> "subprocess.Popen[bytes]":
        try:
            # An argument list from a checked McpCommand, no shell, its own session, a bare environment.
            return subprocess.Popen(  # nosec B603
                list(command),
                cwd=workdir,
                env=dict(env),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as error:
            raise ApplicationError(
                code="MCP_SERVER_START_FAILED",
                message=f"the MCP server could not be started: {error.strerror or type(error).__name__}",
                http_status=502,
            ) from error

    def _read_stdout(self) -> None:
        while True:
            line = self._stdout.readline(self.MAX_LINE_BYTES + 1)
            if not line:
                break
            if len(line) > self.MAX_LINE_BYTES and not line.endswith(b"\n"):
                self._stop_for(f"sent a line longer than {self.MAX_LINE_BYTES} bytes")
                break
            if line.strip():
                self._offer(line)
        self._offer(None)

    def _offer(self, item: bytes | None) -> None:
        while not self._stopped.is_set():
            try:
                self._lines.put(item, timeout=0.1)
                return
            except queue.Full:
                continue

    def _read_stderr(self) -> None:
        while chunk := self._stderr.read(4096):
            with self._guard:
                self._tail = (self._tail + chunk)[-self.TAIL_BYTES :]

    def _watch(self) -> None:
        deadline = time.monotonic() + self._limits.timeout_seconds
        while not self._stopped.wait(self._sample_seconds):
            problem = self._over_limit(deadline)
            if problem:
                self._stop_for(problem)
                return

    def _over_limit(self, deadline: float) -> str | None:
        if time.monotonic() >= deadline:
            return f"ran past its session limit of {self._limits.timeout_seconds:g} seconds"
        memory = self._meter.memory_bytes(self._process.pid)
        if memory > self._limits.max_memory_bytes:
            return (
                f"used {self._mib(memory)} of memory, over its limit of "
                f"{self._mib(self._limits.max_memory_bytes)}"
            )
        disk = self._meter.disk_bytes(self._workdir)
        if disk > self._limits.max_disk_bytes:
            return (
                f"wrote {self._mib(disk)} to disk, over its limit of "
                f"{self._mib(self._limits.max_disk_bytes)}"
            )
        return None

    @staticmethod
    def _mib(size: int) -> str:
        return f"{size / 2**20:.0f} MiB"

    def _stop_for(self, reason: str) -> None:
        with self._guard:
            if self._violation is None:
                self._violation = reason
        self._kill()

    def _kill(self) -> None:
        try:
            self._kill_group(self._process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            # Nothing is left to kill. A group whose leader has exited but is not yet reaped (which
            # is how it is kept, so its id stays ours) is "no such process" on Linux and EPERM on macOS.
            pass

    def _gone(self) -> ApplicationError:
        self._threads[1].join(self.JOIN_SECONDS)  # let the last of its error output arrive
        with self._guard:
            violation, tail = self._violation, self._tail
        if violation:
            return ApplicationError(
                code="MCP_SERVER_LIMIT",
                message=f"the MCP server {violation} and was stopped",
                http_status=502,
            )
        shown = tail.decode("utf-8", errors="replace").strip()[-self.SHOWN_CHARACTERS :]
        said = f" Its last words on stderr: {shown!r}" if shown else ""
        return ApplicationError(
            code="MCP_SERVER_CLOSED",
            message=f"the MCP server closed its output.{said}",
            http_status=502,
        )

    @staticmethod
    def _invalid(what: str) -> ApplicationError:
        return ApplicationError(
            code="MCP_REPLY_INVALID",
            message=f"the MCP server sent {what}",
            http_status=502,
        )
