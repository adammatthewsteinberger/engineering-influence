# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Agent Client Protocol sessions, so a client can load one after it reconnects.

The table is created only if it is missing, the same as the baseline's tables.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the ACP session table when it does not exist yet."""
    if not sa.inspect(op.get_bind()).has_table("acpsessionrecord"):
        op.create_table(
            "acpsessionrecord",
            sa.Column("session_id", sa.String(), primary_key=True),
            sa.Column("cwd", sa.String(), nullable=False),
            sa.Column("run_id", sa.String(), nullable=True),
        )


def downgrade() -> None:
    """Drop the ACP session table when it exists."""
    if sa.inspect(op.get_bind()).has_table("acpsessionrecord"):
        op.drop_table("acpsessionrecord")
