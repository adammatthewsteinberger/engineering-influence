"""The packaged migrations: they build the schema the models describe and upgrade old databases."""

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlmodel import Session, SQLModel, select

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.schema_migrator import SchemaMigrator
from engineering_influence.repositories.acp_session_record import AcpSessionRecord
from engineering_influence.repositories.artifact_record import ArtifactRecord
from engineering_influence.repositories.book_run_record import BookRunRecord
from engineering_influence.repositories.journal_record import JournalRecord
from engineering_influence.repositories.ledger_event_record import LedgerEventRecord
from engineering_influence.repositories.outbox_record import OutboxRecord

TABLES = {
    "acpsessionrecord",
    "artifactrecord",
    "bookrunrecord",
    "journalrecord",
    "ledgereventrecord",
    "outboxrecord",
}
HEAD = "0004"


def fresh_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'fresh.db'}"


def tables_in(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def test_a_new_database_is_brought_to_the_latest_revision(tmp_path: Path) -> None:
    url = fresh_url(tmp_path)
    migrator = SchemaMigrator()
    assert migrator.current(url) is None
    migrator.upgrade(url)
    assert migrator.current(url) == HEAD
    assert tables_in(url) == TABLES


def test_the_migrations_build_exactly_what_the_models_describe(tmp_path: Path) -> None:
    url = fresh_url(tmp_path)
    SchemaMigrator().upgrade(url)
    assert {
        LedgerEventRecord.__tablename__,
        OutboxRecord.__tablename__,
        BookRunRecord.__tablename__,
        JournalRecord.__tablename__,
        ArtifactRecord.__tablename__,
        AcpSessionRecord.__tablename__,
    } == TABLES
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            differences = compare_metadata(
                MigrationContext.configure(connection), SQLModel.metadata
            )
    finally:
        engine.dispose()
    assert differences == []


def test_upgrading_twice_changes_nothing(tmp_path: Path) -> None:
    url = fresh_url(tmp_path)
    migrator = SchemaMigrator()
    migrator.upgrade(url)
    migrator.upgrade(url)
    assert migrator.current(url) == HEAD
    assert tables_in(url) == TABLES


def test_a_database_made_by_create_all_is_adopted_with_its_rows_intact(tmp_path: Path) -> None:
    url = fresh_url(tmp_path)
    engine = create_engine(url)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(LedgerEventRecord(event_name="pipeline.started", payload_json="{}"))
        session.commit()
    engine.dispose()

    migrator = SchemaMigrator()
    assert migrator.current(url) is None
    migrator.upgrade(url)

    assert migrator.current(url) == HEAD
    engine = create_engine(url)
    try:
        with Session(engine) as session:
            assert [row.event_name for row in session.exec(select(LedgerEventRecord)).all()] == [
                "pipeline.started"
            ]
    finally:
        engine.dispose()


def test_a_database_with_only_the_original_tables_gains_the_new_ones(tmp_path: Path) -> None:
    url = fresh_url(tmp_path)
    engine = create_engine(url)
    SQLModel.metadata.create_all(
        engine,
        tables=[LedgerEventRecord.__table__, OutboxRecord.__table__],  # type: ignore[attr-defined]
    )
    engine.dispose()
    assert tables_in(url) == {"ledgereventrecord", "outboxrecord"}

    SchemaMigrator().upgrade(url)

    assert tables_in(url) == TABLES


def test_the_baseline_can_be_undone(tmp_path: Path) -> None:
    url = fresh_url(tmp_path)
    migrator = SchemaMigrator()
    migrator.upgrade(url)
    command.downgrade(migrator._config(url), "base")
    assert tables_in(url) == set()
    assert migrator.current(url) is None


def test_undoing_the_session_table_tolerates_it_already_being_gone(tmp_path: Path) -> None:
    url = fresh_url(tmp_path)
    migrator = SchemaMigrator()
    migrator.upgrade(url)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE acpsessionrecord"))
    engine.dispose()
    command.downgrade(migrator._config(url), "base")
    assert tables_in(url) == set()


def test_checking_a_database_that_was_never_migrated_says_to_upgrade(tmp_path: Path) -> None:
    with pytest.raises(ApplicationError) as raised:
        SchemaMigrator().check(fresh_url(tmp_path))
    assert raised.value.code == "SCHEMA_OUT_OF_DATE"
    assert "ei db upgrade" in raised.value.message


def test_checking_a_current_database_passes(database_url: str) -> None:
    SchemaMigrator().check(database_url)


def test_an_unreachable_database_is_reported_without_its_password() -> None:
    url = "postgresql+psycopg://ei:hunter2-secret@127.0.0.1:1/ei"
    migrator = SchemaMigrator()
    for action in (migrator.upgrade, migrator.current, migrator.check):
        with pytest.raises(ApplicationError) as raised:
            action(url)
        assert raised.value.code == "DATABASE_UNAVAILABLE"
        assert "hunter2" not in raised.value.message
        assert "OperationalError" in raised.value.message


def test_undoing_the_selection_column_tolerates_it_already_being_gone(tmp_path: Path) -> None:
    url = fresh_url(tmp_path)
    migrator = SchemaMigrator()
    migrator.upgrade(url)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE acpsessionrecord DROP COLUMN servers"))
    engine.dispose()
    command.downgrade(migrator._config(url), "0002")
    assert "servers" not in {
        c["name"] for c in inspect(create_engine(url)).get_columns("acpsessionrecord")
    }


def test_undoing_the_approval_column_tolerates_it_already_being_gone(tmp_path: Path) -> None:
    url = fresh_url(tmp_path)
    migrator = SchemaMigrator()
    migrator.upgrade(url)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE acpsessionrecord DROP COLUMN approved"))
    engine.dispose()
    command.downgrade(migrator._config(url), "0003")
    assert "approved" not in {
        c["name"] for c in inspect(create_engine(url)).get_columns("acpsessionrecord")
    }
