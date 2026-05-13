"""marketing: interaction jobs queue

Revision ID: 0004_marketing_interaction_jobs
Revises: 0003_mkt_track_interact
Create Date: 2026-05-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_marketing_interaction_jobs"
down_revision = "0003_mkt_track_interact"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mkt_interaction_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("account_profile_id", sa.Integer(), sa.ForeignKey("mkt_platform_profiles.id"), nullable=True),
        sa.Column("targets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mkt_interaction_jobs_platform", "mkt_interaction_jobs", ["platform"], unique=False)
    op.create_index("ix_mkt_interaction_jobs_event_type", "mkt_interaction_jobs", ["event_type"], unique=False)
    op.create_index("ix_mkt_interaction_jobs_status", "mkt_interaction_jobs", ["status"], unique=False)
    op.create_index("ix_mkt_interaction_jobs_account_profile_id", "mkt_interaction_jobs", ["account_profile_id"], unique=False)
    op.create_index("ix_mkt_interaction_jobs_created_at", "mkt_interaction_jobs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mkt_interaction_jobs_created_at", table_name="mkt_interaction_jobs")
    op.drop_index("ix_mkt_interaction_jobs_account_profile_id", table_name="mkt_interaction_jobs")
    op.drop_index("ix_mkt_interaction_jobs_status", table_name="mkt_interaction_jobs")
    op.drop_index("ix_mkt_interaction_jobs_event_type", table_name="mkt_interaction_jobs")
    op.drop_index("ix_mkt_interaction_jobs_platform", table_name="mkt_interaction_jobs")
    op.drop_table("mkt_interaction_jobs")
