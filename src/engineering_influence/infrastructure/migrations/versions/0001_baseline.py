# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Baseline: the ledger, the outbox, the runs, the journal and the artifacts.

Databases created by the earlier ``create_all()`` already hold some of these tables, so each one
is created only if it is missing; upgrading such a database just records the revision.

Timestamps are timezone-aware, as the models' ``UTCDateTime`` type is: on PostgreSQL that is
``TIMESTAMP WITH TIME ZONE``, so an aware UTC value is stored as the instant it names.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TABLES = (
    "artifactrecord",
    "journalrecord",
    "bookrunrecord",
    "outboxrecord",
    "ledgereventrecord",
)


def _missing(name: str) -> bool:
    return not sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if _missing("ledgereventrecord"):
        op.create_table(
            "ledgereventrecord",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_name", sa.String(), nullable=False),
            sa.Column("payload_json", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if _missing("outboxrecord"):
        op.create_table(
            "outboxrecord",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_id", sa.String(), nullable=False),
            sa.Column("url", sa.String(), nullable=False),
            sa.Column("event_name", sa.String(), nullable=False),
            sa.Column("payload_json", sa.String(), nullable=False),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("dead_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_outboxrecord_event_id", "outboxrecord", ["event_id"], unique=True)
    if _missing("bookrunrecord"):
        op.create_table(
            "bookrunrecord",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("run_id", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("stage", sa.String(), nullable=False),
            sa.Column("document_json", sa.String(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_bookrunrecord_run_id", "bookrunrecord", ["run_id"], unique=True)
    if _missing("journalrecord"):
        op.create_table(
            "journalrecord",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("run_id", sa.String(), nullable=False),
            sa.Column("stage", sa.String(), nullable=False),
            sa.Column("attempt", sa.Integer(), nullable=False),
            sa.Column("digest", sa.String(), nullable=False),
            sa.Column("model", sa.String(), nullable=False),
            sa.Column("params_hash", sa.String(), nullable=False),
            sa.Column("prompt_version", sa.String(), nullable=False),
            sa.Column("context_hash", sa.String(), nullable=False),
            sa.Column("response", sa.String(), nullable=False),
            sa.Column("cost_micro_usd", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("run_id", "stage", "digest"),
        )
        op.create_index("ix_journalrecord_run_id", "journalrecord", ["run_id"])
    if _missing("artifactrecord"):
        op.create_table(
            "artifactrecord",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("run_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("digest", sa.String(), nullable=False),
            sa.Column("data", sa.LargeBinary(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("run_id", "name"),
        )
        op.create_index("ix_artifactrecord_run_id", "artifactrecord", ["run_id"])


def downgrade() -> None:
    for name in TABLES:
        op.drop_table(name)
