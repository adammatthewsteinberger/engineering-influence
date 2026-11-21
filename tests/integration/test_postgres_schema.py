"""The migrations on a real PostgreSQL, not only on the SQLite the unit tests use."""

from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlmodel import Session, SQLModel, select

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.schema_migrator import SchemaMigrator
from engineering_influence.repositories.artifact_record import ArtifactRecord
from engineering_influence.repositories.book_run_record import BookRunRecord
from engineering_influence.repositories.journal_record import JournalRecord
from engineering_influence.repositories.ledger_event_record import LedgerEventRecord
from engineering_influence.repositories.outbox_record import OutboxRecord

pytestmark = pytest.mark.integration

TABLES = {"artifactrecord", "bookrunrecord", "journalrecord", "ledgereventrecord", "outboxrecord"}
MODELS = (ArtifactRecord, BookRunRecord, JournalRecord, LedgerEventRecord, OutboxRecord)


def tables_in(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def test_a_new_schema_is_brought_to_the_latest_revision(postgres_url: str) -> None:
    migrator = SchemaMigrator()
    assert migrator.current(postgres_url) is None
    migrator.upgrade(postgres_url)
    assert migrator.current(postgres_url) == "0001"
    assert tables_in(postgres_url) == TABLES
    assert {model.__tablename__ for model in MODELS} == TABLES


def test_the_migrations_build_exactly_what_the_models_describe_on_postgresql(
    postgres_url: str,
) -> None:
    SchemaMigrator().upgrade(postgres_url)
    engine = create_engine(postgres_url)
    try:
        with engine.connect() as connection:
            differences = compare_metadata(
                MigrationContext.configure(connection), SQLModel.metadata
            )
    finally:
        engine.dispose()
    assert differences == []


def test_upgrading_twice_changes_nothing(postgres_url: str) -> None:
    migrator = SchemaMigrator()
    migrator.upgrade(postgres_url)
    migrator.upgrade(postgres_url)
    assert migrator.current(postgres_url) == "0001"
    assert tables_in(postgres_url) == TABLES


def test_a_database_made_by_create_all_is_adopted_with_its_rows_intact(postgres_url: str) -> None:
    engine = create_engine(postgres_url)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(LedgerEventRecord(event_name="pipeline.started", payload_json="{}"))
        session.commit()

    migrator = SchemaMigrator()
    assert migrator.current(postgres_url) is None
    migrator.upgrade(postgres_url)

    assert migrator.current(postgres_url) == "0001"
    with Session(engine) as session:
        rows = session.exec(select(LedgerEventRecord)).all()
    engine.dispose()
    assert [row.event_name for row in rows] == ["pipeline.started"]


def test_the_baseline_can_be_undone_and_redone(postgres_url: str) -> None:
    migrator = SchemaMigrator()
    migrator.upgrade(postgres_url)
    command.downgrade(migrator._config(postgres_url), "base")
    assert tables_in(postgres_url) == set()
    migrator.upgrade(postgres_url)
    assert tables_in(postgres_url) == TABLES


def test_checking_a_schema_that_was_never_migrated_says_to_upgrade(postgres_url: str) -> None:
    with pytest.raises(ApplicationError) as raised:
        SchemaMigrator().check(postgres_url)
    assert raised.value.code == "SCHEMA_OUT_OF_DATE"


def test_a_timestamp_keeps_the_instant_it_was_written_under_any_session_time_zone(
    postgres_url: str,
) -> None:
    """A timezone-naive column would shift an aware UTC value into the session's own zone."""
    SchemaMigrator().upgrade(postgres_url)
    url = make_url(postgres_url)
    options = f"{url.query['options']} -c TimeZone=Asia/Tokyo"
    engine = create_engine(url.update_query_dict({"options": options}, append=False))
    instant = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    with Session(engine) as session:
        session.add(
            LedgerEventRecord(event_name="pipeline.started", payload_json="{}", created_at=instant)
        )
        session.commit()
    with Session(engine) as session:
        stored = session.exec(select(LedgerEventRecord)).one().created_at
    engine.dispose()
    assert stored == instant
    assert stored.tzinfo is not None
