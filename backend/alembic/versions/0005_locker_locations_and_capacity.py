"""Add campus locations, locker types, and shared locker assignments.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("lockers", sa.Column("block", sa.String(length=2), nullable=True))
    op.add_column("lockers", sa.Column("floor", sa.Integer(), nullable=True))
    op.add_column("lockers", sa.Column("locker_type", sa.String(length=32), nullable=True))

    with op.batch_alter_table("assignments", recreate="always") as batch:
        batch.drop_index("uq_assignments_one_active_per_locker")
        batch.create_index(
            "uq_assignments_one_active_per_locker_student",
            ["locker_id", "student_id"],
            unique=True,
            sqlite_where=sa.text("ended_at IS NULL"),
            postgresql_where=sa.text("ended_at IS NULL"),
        )


def downgrade():
    with op.batch_alter_table("assignments", recreate="always") as batch:
        batch.drop_index("uq_assignments_one_active_per_locker_student")
        batch.create_index(
            "uq_assignments_one_active_per_locker",
            ["locker_id"],
            unique=True,
            sqlite_where=sa.text("ended_at IS NULL"),
            postgresql_where=sa.text("ended_at IS NULL"),
        )

    op.drop_column("lockers", "locker_type")
    op.drop_column("lockers", "floor")
    op.drop_column("lockers", "block")
