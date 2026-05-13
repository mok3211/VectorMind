from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)  # admin/operator/user
    name: str
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Permission(SQLModel, table=True):
    __tablename__ = "permissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)  # e.g. marketing.view
    name: str
    description: str | None = None
    group: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    role_id: int = Field(foreign_key="roles.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RolePermission(SQLModel, table=True):
    __tablename__ = "role_permissions"

    role_id: int = Field(foreign_key="roles.id", primary_key=True)
    permission_id: int = Field(foreign_key="permissions.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MenuModule(SQLModel, table=True):
    """
    可分配的菜单模块（给前端 SideNav 用）：
    - permission_code 为空表示所有登录用户可见
    - 否则需要具备对应 permission 才可见
    """

    __tablename__ = "menu_modules"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)  # e.g. marketing
    label: str
    path: str
    icon: str | None = None
    permission_code: str | None = Field(default=None, index=True)
    sort_order: int = Field(default=100, index=True)
    enabled: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentRun(SQLModel, table=True):
    __tablename__ = "agent_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent: str = Field(index=True)
    input_json: str
    output_text: str
    model: str | None = None
    prompt_version: str | None = None
    steps_json: str | None = None
    assets_json: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class MediaAccount(SQLModel, table=True):
    """
    媒体账号“登录信息”占位表。

    说明：
    - 不建议存明文密码
    - 真正自动化发布一般需要 cookies/session/token（以及定期刷新）
    - 首版先提供 CRUD 管理与状态字段，后续再接 Playwright/官方 API
    """

    __tablename__ = "media_accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str = Field(index=True)  # xhs / douyin / etc.
    nickname: str | None = None
    status: str = Field(default="disconnected")  # disconnected / connected / expired
    notes: str | None = None

    # 以 json 字符串存（后续可升级 JSONB）
    auth_json: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Executor(SQLModel, table=True):
    """
    本地小助手（执行器）注册表：
    - Server 端负责发放 token
    - Local Agent 使用 token 调用 server 的 ingest/心跳接口
    """

    __tablename__ = "executors"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    token: str = Field(index=True, unique=True)
    enabled: bool = Field(default=True, index=True)
    last_seen_at: datetime | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SubscriptionPlan(SQLModel, table=True):
    __tablename__ = "subscription_plans"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)  # free/pro/vip
    name: str
    description: str | None = None
    currency: str = Field(default="CNY")
    price_month: float = Field(default=0.0)
    price_quarter: float = Field(default=0.0)
    price_year: float = Field(default=0.0)
    active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserSubscription(SQLModel, table=True):
    __tablename__ = "user_subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    plan_id: int = Field(foreign_key="subscription_plans.id", index=True)
    status: str = Field(default="active", index=True)  # active/expired/canceled
    start_at: datetime = Field(default_factory=datetime.utcnow)
    end_at: datetime | None = Field(default=None, index=True)
    auto_renew: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
