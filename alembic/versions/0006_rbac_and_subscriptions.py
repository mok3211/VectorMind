"""rbac + subscriptions + menu modules

Revision ID: 0006_rbac_subs
Revises: 0005_executors
Create Date: 2026-05-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_rbac_subs"
down_revision = "0005_executors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ux_roles_code", "roles", ["code"], unique=True)

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("group", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ux_permissions_code", "permissions", ["code"], unique=True)
    op.create_index("ix_permissions_group", "permissions", ["group"], unique=False)

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True, nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"], unique=False)
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), primary_key=True, nullable=False),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id"), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"], unique=False)
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"], unique=False)

    op.create_table(
        "menu_modules",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("permission_code", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ux_menu_modules_key", "menu_modules", ["key"], unique=True)
    op.create_index("ix_menu_modules_permission_code", "menu_modules", ["permission_code"], unique=False)
    op.create_index("ix_menu_modules_sort_order", "menu_modules", ["sort_order"], unique=False)
    op.create_index("ix_menu_modules_enabled", "menu_modules", ["enabled"], unique=False)

    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(), nullable=False, server_default=sa.text("'CNY'")),
        sa.Column("price_month", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("price_quarter", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("price_year", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ux_subscription_plans_code", "subscription_plans", ["code"], unique=True)
    op.create_index("ix_subscription_plans_active", "subscription_plans", ["active"], unique=False)

    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("subscription_plans.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'active'")),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("end_at", sa.DateTime(), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"], unique=False)
    op.create_index("ix_user_subscriptions_plan_id", "user_subscriptions", ["plan_id"], unique=False)
    op.create_index("ix_user_subscriptions_status", "user_subscriptions", ["status"], unique=False)
    op.create_index("ix_user_subscriptions_end_at", "user_subscriptions", ["end_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_subscriptions_end_at", table_name="user_subscriptions")
    op.drop_index("ix_user_subscriptions_status", table_name="user_subscriptions")
    op.drop_index("ix_user_subscriptions_plan_id", table_name="user_subscriptions")
    op.drop_index("ix_user_subscriptions_user_id", table_name="user_subscriptions")
    op.drop_table("user_subscriptions")

    op.drop_index("ix_subscription_plans_active", table_name="subscription_plans")
    op.drop_index("ux_subscription_plans_code", table_name="subscription_plans")
    op.drop_table("subscription_plans")

    op.drop_index("ix_menu_modules_enabled", table_name="menu_modules")
    op.drop_index("ix_menu_modules_sort_order", table_name="menu_modules")
    op.drop_index("ix_menu_modules_permission_code", table_name="menu_modules")
    op.drop_index("ux_menu_modules_key", table_name="menu_modules")
    op.drop_table("menu_modules")

    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")
    op.drop_index("ix_role_permissions_role_id", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index("ix_user_roles_role_id", table_name="user_roles")
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_index("ix_permissions_group", table_name="permissions")
    op.drop_index("ux_permissions_code", table_name="permissions")
    op.drop_table("permissions")

    op.drop_index("ux_roles_code", table_name="roles")
    op.drop_table("roles")

