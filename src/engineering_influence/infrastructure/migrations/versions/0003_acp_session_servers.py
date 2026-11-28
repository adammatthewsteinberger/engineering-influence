# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The MCP servers a session selected, as a JSON list. A session stored before this has none, so existing rows get an
empty list and keep working.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Revision 0002 creates the table before this runs, so only the column needs checking.
    inspector = sa.inspect(op.get_bind())
    if "servers" not in {column["name"] for column in inspector.get_columns("acpsessionrecord")}:
        op.add_column(
            "acpsessionrecord",
            sa.Column("servers", sa.String(), nullable=False, server_default="[]"),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("acpsessionrecord"):
        return
    if "servers" in {column["name"] for column in inspector.get_columns("acpsessionrecord")}:
        with op.batch_alter_table("acpsessionrecord") as batch:
            batch.drop_column("servers")
