"""executors table

Revision ID: 0005_executors
Revises: 0004_marketing_interaction_jobs
Create Date: 2026-05-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_executors"
down_revision = "0004_marketing_interaction_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "executors",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ux_executors_name", "executors", ["name"], unique=True)
    op.create_index("ux_executors_token", "executors", ["token"], unique=True)
    op.create_index("ix_executors_enabled", "executors", ["enabled"], unique=False)
    op.create_index("ix_executors_last_seen_at", "executors", ["last_seen_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_executors_last_seen_at", table_name="executors")
    op.drop_index("ix_executors_enabled", table_name="executors")
    op.drop_index("ux_executors_token", table_name="executors")
    op.drop_index("ux_executors_name", table_name="executors")
    op.drop_table("executors")

