"""Coverage tests for interaction and abstract port contracts."""

import pytest

from engineering_influence.interaction.cli.main import CliApplication, main
from engineering_influence.interfaces.ledger_port import LedgerPort
from engineering_influence.interfaces.queue_port import QueuePort
from engineering_influence.services.interfaces.start_pipeline_interface import (
    StartPipelineInterface,
)


def test_cli_accepts_empty_arguments() -> None:
    assert CliApplication().run([]) == 0


def test_cli_main_exits_with_application_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ei"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 0


def test_abstract_port_bodies_are_fail_closed() -> None:
    class LedgerProbe(LedgerPort):
        def append(self, event_name: str, payload: dict[str, object]) -> None:
            super().append(event_name, payload)

    class QueueProbe(QueuePort):
        def enqueue(self, kind: str, payload: dict[str, object]) -> str:
            return super().enqueue(kind, payload)

    with pytest.raises(NotImplementedError):
        LedgerProbe().append("x", {})
    with pytest.raises(NotImplementedError):
        QueueProbe().enqueue("x", {})


def test_abstract_service_body_is_fail_closed() -> None:
    class ServiceProbe(StartPipelineInterface):
        def start(self, project: object) -> str:
            return super().start(project)  # type: ignore[arg-type]

    with pytest.raises(NotImplementedError):
        ServiceProbe().start(object())
