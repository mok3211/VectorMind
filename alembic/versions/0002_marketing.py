"""marketing tables (profiles/sessions/content/metrics/jobs)

Revision ID: 0002_marketing
Revises: 0001_init
Create Date: 2026-05-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_marketing"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mkt_platform_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("profile_type", sa.String(), nullable=False, server_default=sa.text("'owned'")),
        sa.Column("platform_user_id", sa.String(), nullable=True),
        sa.Column("sec_uid", sa.String(), nullable=True),
        sa.Column("user_link", sa.String(), nullable=True),
        sa.Column("nickname", sa.String(), nullable=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("verify_type", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("verify_name", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'active'")),
        sa.Column("risk_status", sa.String(), nullable=False, server_default=sa.text("'normal'")),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mkt_platform_profiles_platform", "mkt_platform_profiles", ["platform"], unique=False)
    op.create_index("ix_mkt_platform_profiles_profile_type", "mkt_platform_profiles", ["profile_type"], unique=False)
    op.create_index("ix_mkt_platform_profiles_platform_user_id", "mkt_platform_profiles", ["platform_user_id"], unique=False)
    op.create_index("ix_mkt_platform_profiles_sec_uid", "mkt_platform_profiles", ["sec_uid"], unique=False)
    op.create_index("ix_mkt_platform_profiles_user_link", "mkt_platform_profiles", ["user_link"], unique=False)
    op.create_index("ix_mkt_platform_profiles_status", "mkt_platform_profiles", ["status"], unique=False)
    op.create_index("ix_mkt_platform_profiles_risk_status", "mkt_platform_profiles", ["risk_status"], unique=False)

    op.create_table(
        "mkt_platform_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("mkt_platform_profiles.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'valid'")),
        sa.Column("last_validated_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("session_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mkt_platform_sessions_profile_id", "mkt_platform_sessions", ["profile_id"], unique=False)
    op.create_index("ix_mkt_platform_sessions_status", "mkt_platform_sessions", ["status"], unique=False)

    op.create_table(
        "mkt_contents",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("mkt_platform_profiles.id"), nullable=True),
        sa.Column("platform_content_id", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False, server_default=sa.text("'content'")),
        sa.Column("url", sa.String(length=512), nullable=True),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mkt_contents_platform", "mkt_contents", ["platform"], unique=False)
    op.create_index("ix_mkt_contents_profile_id", "mkt_contents", ["profile_id"], unique=False)
    op.create_index("ix_mkt_contents_platform_content_id", "mkt_contents", ["platform_content_id"], unique=False)
    op.create_index("ix_mkt_contents_content_type", "mkt_contents", ["content_type"], unique=False)
    op.create_index("ix_mkt_contents_source", "mkt_contents", ["source"], unique=False)
    op.create_index("ux_mkt_contents_platform_content_id", "mkt_contents", ["platform", "platform_content_id"], unique=True)

    op.create_table(
        "mkt_content_metric_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("content_id", sa.Integer(), sa.ForeignKey("mkt_contents.id"), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=True),
        sa.Column("collect_count", sa.Integer(), nullable=True),
        sa.Column("share_count", sa.Integer(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_mkt_content_metric_snapshots_content_id", "mkt_content_metric_snapshots", ["content_id"], unique=False)
    op.create_index("ix_mkt_content_metric_snapshots_captured_at", "mkt_content_metric_snapshots", ["captured_at"], unique=False)
    op.create_index("ux_mkt_content_metric_snapshots", "mkt_content_metric_snapshots", ["content_id", "captured_at"], unique=True)

    op.create_table(
        "mkt_profile_metric_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("mkt_platform_profiles.id"), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("fans", sa.Integer(), nullable=True),
        sa.Column("follows", sa.Integer(), nullable=True),
        sa.Column("interaction", sa.Integer(), nullable=True),
        sa.Column("contents_count", sa.Integer(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_mkt_profile_metric_snapshots_profile_id", "mkt_profile_metric_snapshots", ["profile_id"], unique=False)
    op.create_index("ix_mkt_profile_metric_snapshots_captured_at", "mkt_profile_metric_snapshots", ["captured_at"], unique=False)
    op.create_index("ux_mkt_profile_metric_snapshots", "mkt_profile_metric_snapshots", ["profile_id", "captured_at"], unique=True)

    op.create_table(
        "mkt_comments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("content_id", sa.Integer(), sa.ForeignKey("mkt_contents.id"), nullable=False),
        sa.Column("platform_comment_id", sa.String(), nullable=False),
        sa.Column("parent_comment_id", sa.String(), nullable=True),
        sa.Column("user_sec_uid", sa.String(), nullable=True),
        sa.Column("nickname", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("sub_comment_count", sa.Integer(), nullable=True),
        sa.Column("pictures", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at_platform", sa.DateTime(), nullable=True),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mkt_comments_platform", "mkt_comments", ["platform"], unique=False)
    op.create_index("ix_mkt_comments_content_id", "mkt_comments", ["content_id"], unique=False)
    op.create_index("ix_mkt_comments_platform_comment_id", "mkt_comments", ["platform_comment_id"], unique=False)
    op.create_index("ix_mkt_comments_parent_comment_id", "mkt_comments", ["parent_comment_id"], unique=False)
    op.create_index("ix_mkt_comments_user_sec_uid", "mkt_comments", ["user_sec_uid"], unique=False)
    op.create_index("ux_mkt_comments_platform_comment_id", "mkt_comments", ["platform", "platform_comment_id"], unique=True)

    op.create_table(
        "mkt_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("mkt_platform_profiles.id"), nullable=True),
        sa.Column("content_id", sa.Integer(), sa.ForeignKey("mkt_contents.id"), nullable=True),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("cron", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mkt_jobs_name", "mkt_jobs", ["name"], unique=False)
    op.create_index("ix_mkt_jobs_platform", "mkt_jobs", ["platform"], unique=False)
    op.create_index("ix_mkt_jobs_job_type", "mkt_jobs", ["job_type"], unique=False)
    op.create_index("ix_mkt_jobs_profile_id", "mkt_jobs", ["profile_id"], unique=False)
    op.create_index("ix_mkt_jobs_content_id", "mkt_jobs", ["content_id"], unique=False)
    op.create_index("ix_mkt_jobs_enabled", "mkt_jobs", ["enabled"], unique=False)
    op.create_index("ix_mkt_jobs_created_by_user_id", "mkt_jobs", ["created_by_user_id"], unique=False)

    op.create_table(
        "mkt_job_runs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("mkt_jobs.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'running'")),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_mkt_job_runs_job_id", "mkt_job_runs", ["job_id"], unique=False)
    op.create_index("ix_mkt_job_runs_status", "mkt_job_runs", ["status"], unique=False)
    op.create_index("ix_mkt_job_runs_started_at", "mkt_job_runs", ["started_at"], unique=False)
    op.create_index("ix_mkt_job_runs_finished_at", "mkt_job_runs", ["finished_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mkt_job_runs_finished_at", table_name="mkt_job_runs")
    op.drop_index("ix_mkt_job_runs_started_at", table_name="mkt_job_runs")
    op.drop_index("ix_mkt_job_runs_status", table_name="mkt_job_runs")
    op.drop_index("ix_mkt_job_runs_job_id", table_name="mkt_job_runs")
    op.drop_table("mkt_job_runs")

    op.drop_index("ix_mkt_jobs_created_by_user_id", table_name="mkt_jobs")
    op.drop_index("ix_mkt_jobs_enabled", table_name="mkt_jobs")
    op.drop_index("ix_mkt_jobs_content_id", table_name="mkt_jobs")
    op.drop_index("ix_mkt_jobs_profile_id", table_name="mkt_jobs")
    op.drop_index("ix_mkt_jobs_job_type", table_name="mkt_jobs")
    op.drop_index("ix_mkt_jobs_platform", table_name="mkt_jobs")
    op.drop_index("ix_mkt_jobs_name", table_name="mkt_jobs")
    op.drop_table("mkt_jobs")

    op.drop_index("ux_mkt_comments_platform_comment_id", table_name="mkt_comments")
    op.drop_index("ix_mkt_comments_user_sec_uid", table_name="mkt_comments")
    op.drop_index("ix_mkt_comments_parent_comment_id", table_name="mkt_comments")
    op.drop_index("ix_mkt_comments_platform_comment_id", table_name="mkt_comments")
    op.drop_index("ix_mkt_comments_content_id", table_name="mkt_comments")
    op.drop_index("ix_mkt_comments_platform", table_name="mkt_comments")
    op.drop_table("mkt_comments")

    op.drop_index("ux_mkt_profile_metric_snapshots", table_name="mkt_profile_metric_snapshots")
    op.drop_index("ix_mkt_profile_metric_snapshots_captured_at", table_name="mkt_profile_metric_snapshots")
    op.drop_index("ix_mkt_profile_metric_snapshots_profile_id", table_name="mkt_profile_metric_snapshots")
    op.drop_table("mkt_profile_metric_snapshots")

    op.drop_index("ux_mkt_content_metric_snapshots", table_name="mkt_content_metric_snapshots")
    op.drop_index("ix_mkt_content_metric_snapshots_captured_at", table_name="mkt_content_metric_snapshots")
    op.drop_index("ix_mkt_content_metric_snapshots_content_id", table_name="mkt_content_metric_snapshots")
    op.drop_table("mkt_content_metric_snapshots")

    op.drop_index("ux_mkt_contents_platform_content_id", table_name="mkt_contents")
    op.drop_index("ix_mkt_contents_source", table_name="mkt_contents")
    op.drop_index("ix_mkt_contents_content_type", table_name="mkt_contents")
    op.drop_index("ix_mkt_contents_platform_content_id", table_name="mkt_contents")
    op.drop_index("ix_mkt_contents_profile_id", table_name="mkt_contents")
    op.drop_index("ix_mkt_contents_platform", table_name="mkt_contents")
    op.drop_table("mkt_contents")

    op.drop_index("ix_mkt_platform_sessions_status", table_name="mkt_platform_sessions")
    op.drop_index("ix_mkt_platform_sessions_profile_id", table_name="mkt_platform_sessions")
    op.drop_table("mkt_platform_sessions")

    op.drop_index("ix_mkt_platform_profiles_risk_status", table_name="mkt_platform_profiles")
    op.drop_index("ix_mkt_platform_profiles_status", table_name="mkt_platform_profiles")
    op.drop_index("ix_mkt_platform_profiles_user_link", table_name="mkt_platform_profiles")
    op.drop_index("ix_mkt_platform_profiles_sec_uid", table_name="mkt_platform_profiles")
    op.drop_index("ix_mkt_platform_profiles_platform_user_id", table_name="mkt_platform_profiles")
    op.drop_index("ix_mkt_platform_profiles_profile_type", table_name="mkt_platform_profiles")
    op.drop_index("ix_mkt_platform_profiles_platform", table_name="mkt_platform_profiles")
    op.drop_table("mkt_platform_profiles")

