"""Coverage tests for interaction and abstract port contracts."""

import pytest

from engineering_influence.interfaces.ledger_interface import LedgerInterface
from engineering_influence.interfaces.queue_interface import QueueInterface
from engineering_influence.runtime.cli_runtime import CliRuntime
from engineering_influence.runtime.main import main
from engineering_influence.services.interfaces.start_pipeline_interface import (
    StartPipelineInterface,
)


def test_cli_accepts_empty_arguments() -> None:
    assert CliRuntime().build().run([]) == 0


def test_cli_starts_pipeline(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        CliRuntime()
        .build()
        .run(
            [
                "pipeline",
                "start",
                "--slug",
                "demo",
                "--title",
                "Demo",
                "--postulate",
                "Evidence first.",
            ]
        )
        == 0
    )

    assert capsys.readouterr().out.strip() == '{"job_id": "local-job-1", "project_slug": "demo"}'


def test_cli_main_exits_with_application_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ei"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 0


def test_abstract_port_bodies_are_fail_closed() -> None:
    class LedgerProbe(LedgerInterface):
        def append(self, event_name: str, payload: dict[str, object]) -> None:
            super().append(event_name, payload)

    class QueueProbe(QueueInterface):
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


def start(*extra: str) -> list[str]:
    return ["pipeline", "start", "--slug", "demo", "--title", "Demo", "--postulate", "p", *extra]


def test_a_stage_that_does_not_exist_is_a_usage_error_not_a_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as stopped:
        CliRuntime().build().run(start("--stage", "bogus"))

    assert stopped.value.code == 2
    assert "invalid choice: 'bogus'" in capsys.readouterr().err


def test_every_real_stage_can_be_asked_for(capsys: pytest.CaptureFixture[str]) -> None:
    assert CliRuntime().build().run(start("--stage", "thesis", "--stage", "publish")) == 0
    assert '"project_slug": "demo"' in capsys.readouterr().out


@pytest.mark.parametrize(("flag", "where"), [("--slug", "slug"), ("--title", "title")])
def test_a_blank_value_is_one_line_on_stderr_and_exit_2_not_a_traceback(
    capsys: pytest.CaptureFixture[str], flag: str, where: str
) -> None:
    arguments = ["pipeline", "start", "--slug", "demo", "--title", "Demo", "--postulate", "p"]
    arguments[arguments.index(flag) + 1] = ""

    assert CliRuntime().build().run(arguments) == 2

    captured = capsys.readouterr()
    assert captured.err == f"error: {where}: String should have at least 1 character\n"
    assert captured.out == ""
