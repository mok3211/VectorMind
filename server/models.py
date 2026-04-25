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
