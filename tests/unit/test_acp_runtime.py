"""``ei acp`` is wired the way ``ei run`` is: the same run store, and a database that was never migrated stops it."""

from pathlib import Path

import pytest

from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interactions.acp.application import AcpApplication
from engineering_influence.runtime.cli_runtime import CliRuntime


def test_acp_is_wired_over_the_run_store_when_the_database_is_migrated(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    app = CliRuntime(queue=InMemoryQueue())._acp_application()
    assert isinstance(app, AcpApplication)
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": 1},
    }
    assert app.handle(initialize)[0]["result"]["protocolVersion"] == 1


def test_acp_stops_on_a_database_that_was_never_migrated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", f"sqlite:///{tmp_path / 'fresh.db'}")
    assert CliRuntime().build().run(["acp"]) == 2
    assert "ei db upgrade" in capsys.readouterr().err
