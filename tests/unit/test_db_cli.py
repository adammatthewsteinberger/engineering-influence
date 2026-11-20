"""The ``db`` command group."""

import argparse
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.db_cli import DbCli
from engineering_influence.interfaces.schema_migrator_interface import SchemaMigratorInterface
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.runtime.cli_runtime import CliRuntime


class Secrets(SecretProviderInterface):
    def __init__(self, values: dict[str, str]) -> None:
        self._values = values

    def require(self, name: str) -> str:
        if name not in self._values:
            raise ApplicationError("SECRET_MISSING", f"required secret {name} is not configured")
        return self._values[name]


class Migrator(SchemaMigratorInterface):
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.upgraded: list[str] = []

    def upgrade(self, database_url: str) -> None:
        if self.failure is not None:
            raise self.failure
        self.upgraded.append(database_url)

    def current(self, database_url: str) -> str | None:
        return "0007"

    def check(self, database_url: str) -> None:
        raise NotImplementedError


ARGUMENTS = argparse.Namespace(db_command="upgrade")
URL = "postgresql+psycopg://ei:pw@db/ei"


def cli(migrator: Migrator, secrets: Secrets | None = None) -> DbCli:
    return DbCli(lambda: migrator, lambda: secrets or Secrets({"EI_DATABASE_URL": URL}))


def test_upgrading_runs_the_migrations_and_reports_the_revision(
    capsys: pytest.CaptureFixture[str],
) -> None:
    migrator = Migrator()
    assert cli(migrator).run(ARGUMENTS) == 0
    assert migrator.upgraded == [URL]
    assert capsys.readouterr().out.strip() == "database schema is at revision 0007"


def test_a_missing_database_url_is_reported_and_exits_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    migrator = Migrator()
    assert cli(migrator, Secrets({})).run(ARGUMENTS) == 2
    assert migrator.upgraded == []
    captured = capsys.readouterr()
    assert "EI_DATABASE_URL is not configured" in captured.err
    assert captured.out == ""


def test_a_database_failure_exits_2_with_one_line(capsys: pytest.CaptureFixture[str]) -> None:
    failure = ApplicationError("DATABASE_UNAVAILABLE", "cannot reach or migrate the database")
    assert cli(Migrator(failure)).run(ARGUMENTS) == 2
    err = capsys.readouterr().err
    assert err.strip() == "error: cannot reach or migrate the database"


def test_a_missing_runtime_extra_says_how_to_install_it(capsys: pytest.CaptureFixture[str]) -> None:
    def missing() -> SchemaMigratorInterface:
        raise ImportError("no alembic", name="alembic")

    assert DbCli(missing, lambda: Secrets({"EI_DATABASE_URL": URL})).run(ARGUMENTS) == 1
    err = capsys.readouterr().err
    assert "pip install 'engineering-influence[runtime]'" in err
    assert "alembic is missing" in err


def test_the_real_command_line_migrates_the_database_named_in_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", f"sqlite:///{tmp_path / 'cli.db'}")
    assert CliRuntime().build().run(["db", "upgrade"]) == 0
    assert capsys.readouterr().out.strip() == "database schema is at revision 0001"


def test_the_db_group_needs_a_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        CliRuntime().build().run(["db"])
    assert raised.value.code == 2
    assert "required" in capsys.readouterr().err
