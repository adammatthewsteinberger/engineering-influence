"""``ei acp``: it serves on the streams it is given, and its failures are one line on stderr with an exit status."""

import argparse
import io
import json

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interactions.acp.application import AcpApplication
from engineering_influence.interactions.acp.interfaces.application_interface import (
    AcpApplicationInterface,
)
from engineering_influence.interactions.cli.acp_cli import AcpCli
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_run import BookRun
from engineering_influence.services.brief_reader import BriefReader
from engineering_influence.services.interfaces.cancel_run_interface import CancelRunInterface
from engineering_influence.services.interfaces.create_run_interface import CreateRunInterface
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.run_progress import RunProgress


class NoRuns(CreateRunInterface):
    def create(self, brief: BookBrief) -> BookRun:
        raise AssertionError("initialize starts no run")


class NoCancel(CancelRunInterface):
    def cancel(self, run_id: str) -> BookRun:
        raise AssertionError("initialize cancels no run")


def application() -> AcpApplicationInterface:
    return AcpApplication(
        NoRuns(),
        NoCancel(),
        BriefReader(),
        RunProgress(InMemoryRunRepository()),
        ResolveSpendConsent(InMemoryRunRepository(), InMemoryQueue()),
    )


def cli(
    app: AcpApplicationInterface,
    reader: io.StringIO | None = None,
    writer: io.StringIO | None = None,
) -> AcpCli:
    return AcpCli(lambda: app, reader or io.StringIO(), writer or io.StringIO())


def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    cli(application()).register(commands)
    return parser.parse_args(argv)


def test_the_acp_command_is_registered() -> None:
    assert parse(["acp"]).command == "acp"


def test_it_serves_the_given_reader_to_the_given_writer_and_exits_zero() -> None:
    request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1}}
    reader = io.StringIO(json.dumps(request) + "\n")
    writer = io.StringIO()
    status = cli(application(), reader, writer).run(argparse.Namespace())
    assert status == 0
    assert json.loads(writer.getvalue())["result"]["protocolVersion"] == 1


def test_a_missing_runtime_extra_is_one_line_and_exit_one(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def missing() -> AcpApplicationInterface:
        raise ImportError("no sqlmodel", name="sqlmodel")

    assert AcpCli(missing, io.StringIO(), io.StringIO()).run(argparse.Namespace()) == 1
    err = capsys.readouterr().err
    assert "acp needs the runtime extra" in err
    assert "sqlmodel is missing" in err


def test_a_refused_setup_is_one_line_and_exit_two(capsys: pytest.CaptureFixture[str]) -> None:
    def refused() -> AcpApplicationInterface:
        raise ApplicationError(
            code="SETTINGS_MISSING", message="EI_DATABASE_URL is not set", http_status=500
        )

    assert AcpCli(refused, io.StringIO(), io.StringIO()).run(argparse.Namespace()) == 2
    assert capsys.readouterr().err == "error: EI_DATABASE_URL is not set\n"
