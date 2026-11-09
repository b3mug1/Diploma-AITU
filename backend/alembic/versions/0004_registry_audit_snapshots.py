"""Add registry before/after snapshots to the existing audit log.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("audit_events", sa.Column("before", sa.JSON(), nullable=True))
    op.add_column("audit_events", sa.Column("after", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("audit_events", "after")
    op.drop_column("audit_events", "before")
