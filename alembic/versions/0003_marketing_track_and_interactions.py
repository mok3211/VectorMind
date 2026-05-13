"""marketing: track pools + interaction records

Revision ID: 0003_mkt_track_interact
Revises: 0002_marketing
Create Date: 2026-05-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# 注意：Postgres 默认 alembic_version.version_num 是 varchar(32)，
# 这里保持 revision id <= 32，避免迁移时出现截断错误。
revision = "0003_mkt_track_interact"
down_revision = "0002_marketing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mkt_track_media",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("platform_content_id", sa.String(), nullable=False),
        sa.Column("content_id", sa.Integer(), sa.ForeignKey("mkt_contents.id"), nullable=True),
        sa.Column("url", sa.String(length=512), nullable=True),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("sec_uid", sa.String(), nullable=True),
        sa.Column("nickname", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=False, server_default=sa.text("'external'")),
        sa.Column("create_user", sa.String(), nullable=True),
        sa.Column("is_comment", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_track_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=True),
        sa.Column("share_count", sa.Integer(), nullable=True),
        sa.Column("collect_count", sa.Integer(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mkt_track_media_platform", "mkt_track_media", ["platform"], unique=False)
    op.create_index("ix_mkt_track_media_platform_content_id", "mkt_track_media", ["platform_content_id"], unique=False)
    op.create_index("ix_mkt_track_media_content_id", "mkt_track_media", ["content_id"], unique=False)
    op.create_index("ix_mkt_track_media_sec_uid", "mkt_track_media", ["sec_uid"], unique=False)
    op.create_index("ix_mkt_track_media_source", "mkt_track_media", ["source"], unique=False)
    op.create_index("ix_mkt_track_media_source_type", "mkt_track_media", ["source_type"], unique=False)
    op.create_index("ix_mkt_track_media_create_user", "mkt_track_media", ["create_user"], unique=False)
    op.create_index("ix_mkt_track_media_is_comment", "mkt_track_media", ["is_comment"], unique=False)
    op.create_index("ix_mkt_track_media_status", "mkt_track_media", ["status"], unique=False)
    op.create_index("ix_mkt_track_media_last_track_at", "mkt_track_media", ["last_track_at"], unique=False)
    op.create_index("ix_mkt_track_media_like_count", "mkt_track_media", ["like_count"], unique=False)
    op.create_index("ix_mkt_track_media_comment_count", "mkt_track_media", ["comment_count"], unique=False)
    op.create_index("ix_mkt_track_media_share_count", "mkt_track_media", ["share_count"], unique=False)
    op.create_index("ix_mkt_track_media_collect_count", "mkt_track_media", ["collect_count"], unique=False)
    op.create_index(
        "ux_mkt_track_media_platform_content_id",
        "mkt_track_media",
        ["platform", "platform_content_id"],
        unique=True,
    )

    op.create_table(
        "mkt_track_comments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("platform_content_id", sa.String(), nullable=False),
        sa.Column("content_id", sa.Integer(), sa.ForeignKey("mkt_contents.id"), nullable=True),
        sa.Column("url", sa.String(length=512), nullable=True),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("user_nickname", sa.String(), nullable=True),
        sa.Column("create_user", sa.String(), nullable=True),
        sa.Column("track_status", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_track_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mkt_track_comments_platform", "mkt_track_comments", ["platform"], unique=False)
    op.create_index("ix_mkt_track_comments_platform_content_id", "mkt_track_comments", ["platform_content_id"], unique=False)
    op.create_index("ix_mkt_track_comments_content_id", "mkt_track_comments", ["content_id"], unique=False)
    op.create_index("ix_mkt_track_comments_user_nickname", "mkt_track_comments", ["user_nickname"], unique=False)
    op.create_index("ix_mkt_track_comments_create_user", "mkt_track_comments", ["create_user"], unique=False)
    op.create_index("ix_mkt_track_comments_track_status", "mkt_track_comments", ["track_status"], unique=False)
    op.create_index("ix_mkt_track_comments_last_track_at", "mkt_track_comments", ["last_track_at"], unique=False)
    op.create_index("ix_mkt_track_comments_is_deleted", "mkt_track_comments", ["is_deleted"], unique=False)

    op.create_table(
        "mkt_interaction_records",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("account_profile_id", sa.Integer(), sa.ForeignKey("mkt_platform_profiles.id"), nullable=True),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("status", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mkt_interaction_records_platform", "mkt_interaction_records", ["platform"], unique=False)
    op.create_index("ix_mkt_interaction_records_event_type", "mkt_interaction_records", ["event_type"], unique=False)
    op.create_index("ix_mkt_interaction_records_account_profile_id", "mkt_interaction_records", ["account_profile_id"], unique=False)
    op.create_index("ix_mkt_interaction_records_target", "mkt_interaction_records", ["target"], unique=False)
    op.create_index("ix_mkt_interaction_records_status", "mkt_interaction_records", ["status"], unique=False)
    op.create_index("ix_mkt_interaction_records_created_at", "mkt_interaction_records", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mkt_interaction_records_created_at", table_name="mkt_interaction_records")
    op.drop_index("ix_mkt_interaction_records_status", table_name="mkt_interaction_records")
    op.drop_index("ix_mkt_interaction_records_target", table_name="mkt_interaction_records")
    op.drop_index("ix_mkt_interaction_records_account_profile_id", table_name="mkt_interaction_records")
    op.drop_index("ix_mkt_interaction_records_event_type", table_name="mkt_interaction_records")
    op.drop_index("ix_mkt_interaction_records_platform", table_name="mkt_interaction_records")
    op.drop_table("mkt_interaction_records")

    op.drop_index("ix_mkt_track_comments_is_deleted", table_name="mkt_track_comments")
    op.drop_index("ix_mkt_track_comments_last_track_at", table_name="mkt_track_comments")
    op.drop_index("ix_mkt_track_comments_track_status", table_name="mkt_track_comments")
    op.drop_index("ix_mkt_track_comments_create_user", table_name="mkt_track_comments")
    op.drop_index("ix_mkt_track_comments_user_nickname", table_name="mkt_track_comments")
    op.drop_index("ix_mkt_track_comments_content_id", table_name="mkt_track_comments")
    op.drop_index("ix_mkt_track_comments_platform_content_id", table_name="mkt_track_comments")
    op.drop_index("ix_mkt_track_comments_platform", table_name="mkt_track_comments")
    op.drop_table("mkt_track_comments")

    op.drop_index("ux_mkt_track_media_platform_content_id", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_collect_count", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_share_count", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_comment_count", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_like_count", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_last_track_at", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_status", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_is_comment", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_create_user", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_source_type", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_source", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_sec_uid", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_content_id", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_platform_content_id", table_name="mkt_track_media")
    op.drop_index("ix_mkt_track_media_platform", table_name="mkt_track_media")
    op.drop_table("mkt_track_media")
