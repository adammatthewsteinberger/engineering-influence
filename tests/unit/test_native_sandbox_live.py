# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A real child under the real sandbox: no network, writes only in its own directory.

Skipped where this system cannot run a native sandbox. CI sets EI_REQUIRE_NATIVE_SANDBOX=1, so there a
missing sandbox is a failure, not a skip.
"""

import os
import shutil
import socket
import subprocess  # nosec B404
import sys
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.tools.mcp_server_sandbox import McpServerSandbox

CHILD = """
import socket, sys
port, outside = int(sys.argv[1]), sys.argv[2]
out = []
try:
    socket.create_connection(("127.0.0.1", port), 3).close()
    out.append("network-open")
except OSError:
    out.append("network-closed")
try:
    open(outside, "w").write("x")
    out.append("outside-written")
except OSError:
    out.append("outside-refused")
open("inside.txt", "w").write("ok")
out.append("inside-written")
print(" ".join(out))
"""


def native_sandbox(tmp_path: Path) -> McpServerSandbox | None:
    sandbox = McpServerSandbox(sys.platform, shutil.which, Path.home())
    probe = tmp_path / "probe"
    probe.mkdir()
    try:
        wrapped = sandbox.wrap((sys.executable, "-c", "pass"), probe)
        result = subprocess.run(wrapped, cwd=probe, timeout=30, capture_output=True, check=False)  # nosec B603
    except (ApplicationError, OSError, subprocess.TimeoutExpired):
        return None
    return sandbox if result.returncode == 0 else None


def test_a_confined_child_cannot_reach_the_network_or_write_outside_its_directory(
    tmp_path: Path,
) -> None:
    sandbox = native_sandbox(tmp_path)
    if sandbox is None:
        if os.environ.get("EI_REQUIRE_NATIVE_SANDBOX"):
            pytest.fail("EI_REQUIRE_NATIVE_SANDBOX is set, but no native sandbox runs here")
        pytest.skip("this system cannot run a native sandbox for MCP servers")
    work = tmp_path / "work"
    work.mkdir()
    outside = tmp_path / "outside.txt"
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    try:
        port = listener.getsockname()[1]
        wrapped = sandbox.wrap((sys.executable, "-c", CHILD, str(port), str(outside)), work)
        result = subprocess.run(  # nosec B603
            wrapped, cwd=work, timeout=60, capture_output=True, text=True, check=False
        )
    finally:
        listener.close()
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["network-closed", "outside-refused", "inside-written"]
    assert not outside.exists()
    assert (work / "inside.txt").read_text() == "ok"
