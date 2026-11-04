"""Execute every example as a real subprocess and assert on its output."""

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

EXPECTED = {
    "cli_example.py": "sample-essay",
    "api_example.py": "sample-essay",
    "mcp_example.py": "sample-essay",
    "sdk_sync_example.py": "sample-essay",
    "sdk_async_example.py": "sample-essay",
    "observability_example.py": "job carries id: example-request-0001",
    "webhook_receiver.py": "tampered: False",
    "webhook_sender.py": "replay: duplicate ignored",
}


@pytest.mark.parametrize(("script", "needle"), sorted(EXPECTED.items()))
def test_example_runs(script: str, needle: str) -> None:
    result = subprocess.run(
        [sys.executable, str(EXAMPLES / script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert needle in result.stdout
